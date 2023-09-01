#ifndef OSTAR_RELAY_ANALYSIS_DEPENDENCY_GRAPH_H_
#define OSTAR_RELAY_ANALYSIS_DEPENDENCY_GRAPH_H_

#include <ostar/relay/expr.h>

#include <unordered_map>
#include <vector>

#include "../../support/arena.h"
#include "../transforms/let_list.h"

namespace ostar {
namespace relay {

using support::LinkedList;
using support::LinkNode;

class DependencyGraph {
 public:
  struct Node {
    bool new_scope = false;
    LinkedList<Node*> children;
    LinkedList<Node*> parents;
  };

  std::unordered_map<Expr, Node*, ObjectPtrHash, ObjectPtrEqual> expr_node;

  std::vector<Node*> post_dfs_order;

  static DependencyGraph Create(support::Arena* arena, const Expr& body);

 private:
  class Creator;
};

}  // namespace relay
}  // namespace ostar
#endif  // OSTAR_RELAY_ANALYSIS_DEPENDENCY_GRAPH_H_
