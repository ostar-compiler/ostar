#ifndef OSTAR_RELAY_ANALYSIS_ANNOTATED_REGION_SET_H_
#define OSTAR_RELAY_ANALYSIS_ANNOTATED_REGION_SET_H_

#include <ostar/relay/analysis.h>
#include <ostar/relay/attrs/annotation.h>
#include <ostar/relay/error.h>
#include <ostar/relay/expr.h>
#include <ostar/relay/expr_functor.h>
#include <ostar/relay/transform.h>

#include <list>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

namespace ostar {
namespace relay {

class AnnotatedRegion;
class AnnotatedRegionSet;

class AnnotatedRegionNode : public Object {
 public:
  void VisitAttrs(AttrVisitor* v) {
    v->Visit("id", &id_);
    v->Visit("target", &target_);
    Array<Expr> nodes_array(nodes_.begin(), nodes_.end());
    v->Visit("nodes", &nodes_array);
    Array<Expr> args_array(ins_.begin(), ins_.end());
    v->Visit("args", &args_array);
    Array<Expr> rets_array(outs_.begin(), outs_.end());
    v->Visit("rets", &rets_array);
  }

  int GetID() const { return id_; }

  std::string GetName() const { return func_name_; }

  std::string GetTarget() const { return target_; }

  std::list<Expr> GetInputs() const { return ins_; }

  std::list<Expr> GetOutputs() const { return outs_; }

  std::unordered_set<Expr, ObjectPtrHash, ObjectPtrEqual> GetNodes() const { return nodes_; }

  static constexpr const char* _type_key = "relay.AnnotatedRegion";
  OSTAR_DECLARE_FINAL_OBJECT_INFO(AnnotatedRegionNode, Object);

 protected:
  int id_{-1};
  std::string func_name_ = "default";
  std::string target_ = "default";
  std::list<Expr> ins_;
  std::list<Expr> outs_;
  std::unordered_set<Expr, ObjectPtrHash, ObjectPtrEqual> nodes_;

  friend class AnnotatedRegionSet;
  friend class AnnotatedRegionSetNode;
};

class AnnotatedRegion : public ObjectRef {
 public:
  AnnotatedRegion() {
    auto n = make_object<AnnotatedRegionNode>();
    data_ = std::move(n);
  }

  explicit AnnotatedRegion(ObjectPtr<Object> n) : ObjectRef(n) {}

  AnnotatedRegionNode* operator->() const {
    auto* ptr = get_mutable();
    ICHECK(ptr != nullptr);
    return static_cast<AnnotatedRegionNode*>(ptr);
  }
};

class AnnotatedRegionSetNode : public Object {
  using UnorderedRegionSet = std::unordered_set<AnnotatedRegion, ObjectPtrHash, ObjectPtrEqual>;
  using iterator = UnorderedRegionSet::iterator;
  using const_iterator = UnorderedRegionSet::const_iterator;

 public:
  AnnotatedRegionSetNode() = default;

  iterator begin() { return regions_.begin(); }
  iterator end() { return regions_.end(); }
  const_iterator begin() const { return regions_.begin(); }
  const_iterator end() const { return regions_.end(); }

  AnnotatedRegion GetRegion(const Expr& expr) const;

  void MergeRegions(AnnotatedRegion src, AnnotatedRegion dest);

  void VisitAttrs(AttrVisitor* v) {
    Array<AnnotatedRegion> regions_array(regions_.begin(), regions_.end());
    v->Visit("regions", &regions_array);
  }

  static constexpr const char* _type_key = "relay.AnnotatedRegionSet";
  OSTAR_DECLARE_FINAL_OBJECT_INFO(AnnotatedRegionSetNode, Object);

 private:

  void AddToRegion(AnnotatedRegion dest, const Expr& expr);

  AnnotatedRegion MakeRegion(const std::string& func_name, const std::string& target);

  std::unordered_set<AnnotatedRegion, ObjectPtrHash, ObjectPtrEqual> regions_;
  int region_id_{0};

  friend class AnnotatedRegionSet;
};

class AnnotatedRegionSet : public ObjectRef {
  using UnorderedRegionSet = std::unordered_set<AnnotatedRegion, ObjectPtrHash, ObjectPtrEqual>;
  using iterator = UnorderedRegionSet::iterator;
  using const_iterator = UnorderedRegionSet::const_iterator;

 public:
  AnnotatedRegionSet() {
    auto n = make_object<AnnotatedRegionSetNode>();
    data_ = std::move(n);
  }

  explicit AnnotatedRegionSet(ObjectPtr<Object> n) : ObjectRef(n) {}

  iterator begin() {
    auto* n = operator->();
    ICHECK(n);
    return n->begin();
  }
  iterator end() {
    auto* n = operator->();
    ICHECK(n);
    return n->end();
  }
  const_iterator begin() const {
    const auto* n = operator->();
    ICHECK(n);
    return n->begin();
  }
  const_iterator end() const {
    const auto* n = operator->();
    ICHECK(n);
    return n->end();
  }

  AnnotatedRegionSetNode* operator->() const {
    auto* ptr = get_mutable();
    ICHECK(ptr != nullptr);
    return static_cast<AnnotatedRegionSetNode*>(ptr);
  }

  AnnotatedRegion operator[](const Expr& expr) {
    const auto* n = operator->();
    ICHECK(n);
    return n->GetRegion(expr);
  }

  static AnnotatedRegionSet Create(const Expr& expr, const Op& begin, const Op& end,
                                   const std::string& func_name = "default");

 private:
  class Creator;
};

}  // namespace relay
}  // namespace ostar

#endif 
