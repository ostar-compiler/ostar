#ifndef OSTAR_RELAY_ANALYSIS_CALL_GRAPH_H_
#define OSTAR_RELAY_ANALYSIS_CALL_GRAPH_H_

#include <ostar/ir/module.h>
#include <ostar/relay/expr.h>
#include <ostar/relay/function.h>
#include <ostar/runtime/object.h>

#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace ostar {
namespace relay {

class CallGraphEntry;
class CallGraph;

class CallGraphNode : public Object {
  using CallGraphMap =
      std::unordered_map<GlobalVar, std::unique_ptr<CallGraphEntry>, ObjectPtrHash, ObjectPtrEqual>;
  using iterator = CallGraphMap::iterator;
  using const_iterator = CallGraphMap::const_iterator;

 public:
  IRModule module;

  CallGraphNode() {}

  void VisitAttrs(AttrVisitor* v) { v->Visit("module", &module); }

  void Print(std::ostream& os) const;

  iterator begin() { return call_graph_.begin(); }
  iterator end() { return call_graph_.end(); }
  const_iterator begin() const { return call_graph_.begin(); }
  const_iterator end() const { return call_graph_.end(); }

  const CallGraphEntry* operator[](const GlobalVar& gv) const;

  CallGraphEntry* operator[](const GlobalVar& gv);

  const CallGraphEntry* operator[](const std::string& gvar_name) const {
    return (*this)[module->GetGlobalVar(gvar_name)];
  }

  CallGraphEntry* operator[](const std::string& gvar_name) {
    return (*this)[module->GetGlobalVar(gvar_name)];
  }

  BaseFunc GetGlobalFunction(const GlobalVar& var) const;

  std::vector<CallGraphEntry*> GetEntryGlobals() const;

  GlobalVar RemoveGlobalVarFromModule(CallGraphEntry* cg_node, bool update_call_graph = false);

  CallGraphEntry* LookupGlobalVar(const GlobalVar& gv);

  std::vector<CallGraphEntry*> TopologicalOrder() const;

  static constexpr const char* _type_key = "relay.CallGraph";
  OSTAR_DECLARE_FINAL_OBJECT_INFO(CallGraphNode, Object);

 private:

  void AddToCallGraph(const GlobalVar& gv, const Function& func);

  CallGraphMap call_graph_;

  friend CallGraph;
};

class CallGraph : public ObjectRef {
  using CallGraphMap =
      std::unordered_map<GlobalVar, std::unique_ptr<CallGraphEntry>, ObjectPtrHash, ObjectPtrEqual>;
  using iterator = CallGraphMap::iterator;
  using const_iterator = CallGraphMap::const_iterator;

 public:

  explicit CallGraph(IRModule module);

  explicit CallGraph(ObjectPtr<Object> n) : ObjectRef(n) {}

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

  const CallGraphEntry* operator[](const GlobalVar& gv) const {
    const auto* n = operator->();
    ICHECK(n);
    return (*n)[gv];
  }

  CallGraphEntry* operator[](const GlobalVar& gv) {
    auto* n = operator->();
    ICHECK(n);
    return (*n)[gv];
  }
  const CallGraphEntry* operator[](const std::string& gvar_name) const {
    const auto* n = operator->();
    ICHECK(n);
    return (*n)[gvar_name];
  }
  CallGraphEntry* operator[](const std::string& gvar_name) {
    auto* n = operator->();
    ICHECK(n);
    return (*n)[gvar_name];
  }

  CallGraphNode* operator->() const {
    auto* ptr = get_mutable();
    ICHECK(ptr != nullptr);
    return static_cast<CallGraphNode*>(ptr);
  }

 private:
  friend std::ostream& operator<<(std::ostream& os, const CallGraph&);
};

class CallGraphEntry {
 public:
  using CallGraphEntryPair = std::pair<GlobalVar, CallGraphEntry*>;
  using CallGraphEntryVector = std::vector<CallGraphEntryPair>;
  using CallGraphEntrySet = std::unordered_set<const CallGraphEntry*>;
  using iterator = std::vector<CallGraphEntryPair>::iterator;
  using const_iterator = std::vector<CallGraphEntryPair>::const_iterator;

  explicit CallGraphEntry(const GlobalVar& gv) : global_(gv) {}

  CallGraphEntry(const CallGraphEntry&) = delete;
  CallGraphEntry& operator=(const CallGraphEntry&) = delete;

  iterator begin() { return called_globals_.begin(); }
  iterator end() { return called_globals_.end(); }
  const_iterator begin() const { return called_globals_.begin(); }
  const_iterator end() const { return called_globals_.end(); }

  bool empty() const { return called_globals_.empty(); }

  uint32_t size() const { return static_cast<uint32_t>(called_globals_.size()); }

  CallGraphEntry* operator[](size_t i) const {
    ICHECK_LT(i, called_globals_.size()) << "Invalid Index";
    return called_globals_[i].second;
  }

  void Print(std::ostream& os) const;

  uint32_t GetRefCount() const { return ref_cnt_; }

  GlobalVar GetGlobalVar() const { return global_; }

  std::string GetNameHint() const { return global_->name_hint; }

  bool IsRecursive() const { return is_recursive_; }

  bool IsRecursiveEntry() const { return GetRefCount() == 1 && IsRecursive(); }

  std::vector<CallGraphEntry*> TopologicalOrder(
      CallGraphEntrySet* visited = new CallGraphEntrySet()) const;
  void CleanCallGraphEntries();

  void AddCalledGlobal(CallGraphEntry* cg_node);

  void RemoveCallTo(const GlobalVar& callee);

  void RemoveAllCallTo(CallGraphEntry* callee);

 private:
  void DecRef() {
    ICHECK_GT(ref_cnt_, 0);
    --ref_cnt_;
  }
  void IncRef() { ++ref_cnt_; }

  bool is_recursive_{false};
  uint32_t ref_cnt_{0};
  GlobalVar global_;
  CallGraphEntryVector called_globals_;

  friend class CallGraph;
  friend std::ostream& operator<<(std::ostream& os, const CallGraphEntry&);
};

}  
}
#endif  
