#include "annotated_region_set.h"

#include <ostar/relay/error.h>
#include <ostar/relay/expr.h>

#include <unordered_map>
#include <vector>

namespace ostar {
namespace relay {

AnnotatedRegion AnnotatedRegionSetNode::GetRegion(const Expr& expr) const {
  for (auto candidate : regions_) {
    if (candidate->nodes_.find(expr) != candidate->nodes_.end()) {
      return candidate;
    }
  }
  return AnnotatedRegion(nullptr);
}

void AnnotatedRegionSetNode::MergeRegions(AnnotatedRegion src, AnnotatedRegion dest) {
  if (dest == src) {
    return;
  }

  // Merge src to dest and erase src.
  dest->nodes_.insert(src->nodes_.begin(), src->nodes_.end());
  for (const auto& input : src->ins_) {
    dest->ins_.push_back(input);
  }
  for (const auto& output : src->outs_) {
    dest->outs_.push_back(output);
  }

  std::vector<Expr> ins_to_remove;
  for (const auto& input : dest->ins_) {
    auto call = Downcast<Call>(input);
    auto it = src->nodes_.find(call->args[0]);
    if (it != src->nodes_.end()) {
      dest->outs_.remove(*it);
      ins_to_remove.push_back(input);
    }
  }
  for (const auto& input : ins_to_remove) {
    dest->ins_.remove(input);
  }
  regions_.erase(src);
}

void AnnotatedRegionSetNode::AddToRegion(AnnotatedRegion dest, const Expr& expr) {
  auto src = GetRegion(expr);
  if (src.defined()) {
    MergeRegions(src, dest);
  } else {
    dest->nodes_.insert(expr);
  }
}

AnnotatedRegion AnnotatedRegionSetNode::MakeRegion(const std::string& func_name,
                                                   const std::string& target) {
  auto ret = regions_.emplace(AnnotatedRegion());
  (*ret.first)->id_ = region_id_++;
  (*ret.first)->target_ = target;
  (*ret.first)->func_name_ = func_name;
  return *ret.first;
}

class AnnotatedRegionSet::Creator : protected MixedModeVisitor {
 public:
  Creator(const Op& region_begin_op, const Op& region_end_op,
          const std::string& func_name = "default")
      : begin_op_(region_begin_op), end_op_(region_end_op), func_name_(func_name) {}

  AnnotatedRegionSet Create(const Expr& expr) {
    VisitExpr(expr);
    return std::move(region_set_);
  }

  void AddToArgRegion(Expr expr, Array<Expr> args) {
    AnnotatedRegion region;
    for (auto arg : args) {
      const CallNode* end = arg.as<CallNode>();
      if (end && end->op == end_op_) {  
        continue;
      }

      region = region_set_->GetRegion(arg);
      if (region.defined()) {
        break;
      }
    }

    // Try to merge open regions.
    for (auto arg : args) {
      const CallNode* end = arg.as<CallNode>();
      if (end && end->op == end_op_) {  // Ignore closed regions.
        continue;
      }

      auto arg_region = region_set_->GetRegion(arg);
      ICHECK_EQ(region.defined(), arg_region.defined())
          << "Arg regions are inconsistent: " << AsText(expr);
      if (region.defined() && region != arg_region) {
        region_set_->MergeRegions(arg_region, region);
      }
    }
    if (region.defined()) {
      region_set_->AddToRegion(region, expr);
    }
  }

  void VisitExpr_(const CallNode* call) {
    auto op_node = call->op.as<OpNode>();

    if (op_node == nullptr || call->attrs.as<CompilerAttrs>() == nullptr) {
      AddToArgRegion(GetRef<Call>(call), call->args);
    } else if (call->op == begin_op_) {
      // The annotation node is inserted on edge so it must have only one argument.
      ICHECK_EQ(call->args.size(), 1U);
      std::string target = call->attrs.as<CompilerAttrs>()->compiler;

      // Check if the argument already belongs to a region
      auto region = region_set_->GetRegion(GetRef<Call>(call));
      ICHECK(!region.defined());

      // Create a new region.
      region = region_set_->MakeRegion(func_name_, target);
      region->nodes_.insert(GetRef<Call>(call));
      region->ins_.push_back(GetRef<Call>(call));
    } else {
      ICHECK_EQ(call->op, end_op_);
      ICHECK_EQ(call->args.size(), 1U);
      std::string target = call->attrs.as<CompilerAttrs>()->compiler;

      // Check if the argument already belongs to a region
      auto region = region_set_->GetRegion(call->args[0]);
      if (!region.defined()) {
        throw CompileError(ErrorBuilder()
                           << "Cannot find the corresponding region for end annotation:\n"
                           << AsText(GetRef<Call>(call), false));
      } else {
        ICHECK_EQ(region->GetTarget(), target);
      }
      region->nodes_.insert(GetRef<Call>(call));
      region->outs_.push_back(GetRef<Call>(call));
    }
  }

  void VisitExpr_(const TupleNode* op) { AddToArgRegion(GetRef<Tuple>(op), op->fields); }

  void VisitExpr_(const TupleGetItemNode* g) {
    Array<Expr> args = {g->tuple};
    AddToArgRegion(GetRef<TupleGetItem>(g), args);
  }

  void VisitExpr_(const LetNode* op) {
    Array<Expr> args = {op->var, op->value, op->body};
    AddToArgRegion(GetRef<Let>(op), args);
    ExprVisitor::VisitExpr_(op);
  }

  void VisitExpr_(const IfNode* op) {
    Array<Expr> args = {op->cond, op->true_branch, op->false_branch};
    AddToArgRegion(GetRef<If>(op), args);
    ExprVisitor::VisitExpr_(op);
  }

  void VisitExpr_(const RefCreateNode* op) {
    Array<Expr> args = {op->value};
    AddToArgRegion(GetRef<RefCreate>(op), args);
    ExprVisitor::VisitExpr_(op);
  }

  void VisitExpr_(const RefReadNode* op) {
    Array<Expr> args = {op->ref};
    AddToArgRegion(GetRef<RefRead>(op), args);
    ExprVisitor::VisitExpr_(op);
  }

  void VisitExpr_(const RefWriteNode* op) {
    Array<Expr> args = {op->ref};
    AddToArgRegion(GetRef<RefWrite>(op), args);
    ExprVisitor::VisitExpr_(op);
  }

 private:
  AnnotatedRegionSet region_set_;
  const Op begin_op_;
  const Op end_op_;
  const std::string func_name_;
};

AnnotatedRegionSet AnnotatedRegionSet::Create(const Expr& expr, const Op& begin, const Op& end,
                                              const std::string& func_name) {
  return Creator(begin, end, func_name).Create(expr);
}

OSTAR_REGISTER_NODE_TYPE(AnnotatedRegionNode);
OSTAR_REGISTER_NODE_TYPE(AnnotatedRegionSetNode);

OSTAR_REGISTER_GLOBAL("relay.analysis.AnnotatedRegionSet")
    .set_body_typed([](Expr expr, Op begin, Op end) {
      return AnnotatedRegionSet::Create(expr, begin, end);
    });

OSTAR_REGISTER_GLOBAL("relay.analysis.GetRegion")
    .set_body_typed([](AnnotatedRegionSet region_set, Expr expr) {
      return region_set->GetRegion(expr);
    });

}  // namespace relay
}  // namespace ostar
