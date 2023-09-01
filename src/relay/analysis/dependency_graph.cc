#include "dependency_graph.h"

#include <ostar/relay/expr_functor.h>

#include <unordered_set>
#include <utility>

namespace ostar {
namespace relay {

class DependencyGraph::Creator : private MixedModeVisitor {
 public:
  explicit Creator(support::Arena* arena) : arena_(arena) {}

  DependencyGraph Create(const Expr& body) {
    this->VisitExpr(body);
    return std::move(graph_);
  }

 private:
  support::Arena* arena_;
  DependencyGraph graph_;
  void Depend(DependencyGraph::Node* parent, const Expr& child) {
    VisitExpr(child);

    ICHECK_NE(graph_.expr_node.count(child), 0);

    Depend(parent, graph_.expr_node[child]);
  }

  void Depend(DependencyGraph::Node* parent, DependencyGraph::Node* child) {
    auto* parent_link = arena_->make<LinkNode<DependencyGraph::Node*>>();
    parent_link->value = parent;
    child->parents.Push(parent_link);

    auto* child_link = arena_->make<LinkNode<DependencyGraph::Node*>>();
    child_link->value = child;
    parent->children.Push(child_link);
  }

  std::unordered_set<Expr, ObjectPtrHash, ObjectPtrEqual> visited_;

  DependencyGraph::Node* NewNode(bool new_scope) {
    auto* ret = arena_->make<DependencyGraph::Node>();
    ret->new_scope = new_scope;
    return ret;
  }

  void VisitLeaf(const Expr& e) override {
    if (visited_.count(e) == 0) {
      if (graph_.expr_node.count(e) == 0) {
        graph_.expr_node[e] = NewNode(false);
      }
      visited_.insert(e);
      MixedModeVisitor::VisitLeaf(e);
      graph_.post_dfs_order.push_back(graph_.expr_node[e]);
    }
  }

  void VisitExpr_(const CallNode* c) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(c)];
    Depend(n, c->op);
    for (const auto& a : c->args) {
      Depend(n, a);
    }
  }

  void VisitExpr_(const TupleNode* t) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(t)];
    for (const auto& a : t->fields) {
      Depend(n, a);
    }
  }

  void VisitExpr_(const TupleGetItemNode* t) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(t)];
    Depend(n, t->tuple);
  }

  void VisitExpr_(const RefCreateNode* r) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(r)];
    Depend(n, r->value);
  }

  void VisitExpr_(const RefReadNode* r) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(r)];
    Depend(n, r->ref);
  }

  void VisitExpr_(const RefWriteNode* r) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(r)];
    Depend(n, r->ref);
    Depend(n, r->value);
  }

  void VisitExpr_(const IfNode* i) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(i)];
    DependencyGraph::Node* t = NewNode(true);
    DependencyGraph::Node* f = NewNode(true);
    Depend(n, i->cond);
    Depend(n, t);
    Depend(n, f);
    Depend(t, i->true_branch);
    Depend(f, i->false_branch);
    graph_.post_dfs_order.push_back(f);
    graph_.post_dfs_order.push_back(t);
  }

  void VisitExpr_(const FunctionNode* f) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(f)];
    DependencyGraph::Node* b = NewNode(true);
    Depend(n, b);
    for (const auto& p : f->params) {
      Depend(b, p);
    }
    Depend(b, f->body);
    graph_.post_dfs_order.push_back(b);
  }

  void VisitExpr_(const LetNode* l) final {
    std::unordered_map<const LetNode*, DependencyGraph::Node*> b_map;
    auto pre_visit = [&](const LetNode* op) {
      Expr e = GetRef<Expr>(op);
      if (visited_.count(e) == 0) {
        if (graph_.expr_node.count(e) == 0) {
          graph_.expr_node[e] = NewNode(false);
        }
        visited_.insert(e);
      }
      DependencyGraph::Node* n = graph_.expr_node[e];
      DependencyGraph::Node* b = NewNode(true);
      Depend(n, b);
      Depend(b, op->var);
      Depend(b, op->value);
      b_map[op] = b;
    };
    auto post_visit = [&](const LetNode* op) {
      ICHECK(b_map.count(op));
      DependencyGraph::Node* b = b_map[op];
      Expr e = GetRef<Expr>(op);
      Depend(b, op->body);
      graph_.post_dfs_order.push_back(b);
      if (op != l) {
        this->visit_counter_[op]++;
        graph_.post_dfs_order.push_back(graph_.expr_node[e]);
      }
    };
    ExpandANormalForm(l, pre_visit, post_visit);
  }

  void VisitExpr_(const MatchNode* m) final {
    DependencyGraph::Node* n = graph_.expr_node[GetRef<Expr>(m)];
    Depend(n, m->data);
    std::vector<DependencyGraph::Node*> v;
    for (const Clause& c : m->clauses) {
      DependencyGraph::Node* b = NewNode(true);
      Depend(n, b);
      Depend(b, c->rhs);
      v.push_back(b);
    }
    for (auto it = v.rbegin(); it != v.rend(); ++it) {
      graph_.post_dfs_order.push_back(*it);
    }
  }

  void VisitExpr_(const VarNode* v) final {}

  void VisitExpr_(const GlobalVarNode* v) final {}

  void VisitExpr_(const ConstantNode* c) final {}

  void VisitExpr_(const OpNode* o) final {}

  void VisitExpr_(const ConstructorNode* c) final {}
};

DependencyGraph DependencyGraph::Create(support::Arena* arena, const Expr& body) {
  return Creator(arena).Create(body);
}

}  // namespace relay
}  // namespace ostar
