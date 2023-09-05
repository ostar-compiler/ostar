/*------*/

/*!
 * \file src/relay/analysis/graph_partitioner.h
 * \brief The helper function for op fusion.
 */

#ifndef OSTAR_RELAY_ANALYSIS_GRAPH_PARTITIONER_H_
#define OSTAR_RELAY_ANALYSIS_GRAPH_PARTITIONER_H_

#include <ostar/relay/op_attr_types.h>

#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "../../support/arena.h"

namespace ostar {
namespace relay {

using support::LinkedList;
using support::LinkNode;

class IndexedForwardGraph {
 public:
  struct Node;
  struct Edge {
    Node* node{nullptr};
    OpPatternKind pattern{kOpaque};
  };
  struct Node {
    const ostar::Object* ref{nullptr};
    size_t index{0};
    bool extern_ref{false};
    OpPatternKind pattern{kOpaque};
    LinkedList<Edge> outputs;
  };
  std::unordered_map<const ostar::Object*, Node*> node_map;
  std::vector<Node*> post_dfs_order;

  /*! \brief Dump the graph into string. */
  void DebugDump() {
    std::ostringstream os;
    for (size_t i = 0; i < post_dfs_order.size(); ++i) {
      Node* node = post_dfs_order[i];
      os << "node[" << i << "], " << GetRef<ObjectRef>(node->ref) << " outputs=[";
      for (auto* link = node->outputs.head; link != nullptr; link = link->next) {
        os << link->value.node->index << ", ";
      }
      os << "]\n";
    }
    LOG(INFO) << os.str();
  }
};

class DominatorTree {
 public:
  struct Node {
    IndexedForwardGraph::Node* gnode{nullptr};
    Node* parent{nullptr};
    int depth{0};
    OpPatternKind pattern{kOpaque};
  };
  // index -> node.
  std::vector<Node*> nodes;

  static DominatorTree PostDom(support::Arena* arena, const IndexedForwardGraph& graph);

 private:
  // Combine pattern together.
  inline static OpPatternKind CombinePattern(OpPatternKind lhs, OpPatternKind rhs) {
    if (lhs > rhs) return lhs;
    return rhs;
  }

  static Node* LeastCommonAncestor(Node* lhs, Node* rhs, OpPatternKind* edge_pattern);

  Node* LeastCommonAncestor(const LinkedList<IndexedForwardGraph::Edge>& input_nodes,
                            OpPatternKind* edge_pattern);

  Node* GetNode(support::Arena* arena, IndexedForwardGraph::Node* gnode);
};


class GraphPartitioner {
 public:
  explicit GraphPartitioner(support::Arena* arena, int opt_level, size_t max_fuse_depth)
      : arena_(arena), opt_level_(opt_level), max_fuse_depth_(max_fuse_depth) {}

  struct Group {
    Group* parent{nullptr};
    OpPatternKind pattern;
    const ostar::Object* root_ref{nullptr};

    const ostar::Object* anchor_ref{nullptr};

    uint32_t num_nodes{1};

    runtime::Map<runtime::String, ObjectRef> attrs;

    Group* FindRoot();
  };

  std::vector<Group*> Partition(const IndexedForwardGraph& graph);

 private:
  support::Arena* arena_;
  int opt_level_;
  size_t max_fuse_depth_;
  std::vector<Group*> groups_;
  std::unordered_set<IndexedForwardGraph::Node*> visited_;
  template <typename F>
  bool CheckPath_(IndexedForwardGraph::Node* src, IndexedForwardGraph::Node* sink, F fcond);

  template <typename F>
  bool CheckPath(IndexedForwardGraph::Node* src, IndexedForwardGraph::Node* sink, F fcond);

  void MergeFromTo(Group* child, Group* parent);

  void CommitFuse_(IndexedForwardGraph::Node* src, IndexedForwardGraph::Node* sink, Group* target);

  void CommitFuse(IndexedForwardGraph::Node* src, IndexedForwardGraph::Node* sink);

  size_t CountNodesUptoSink_(IndexedForwardGraph::Node* src, IndexedForwardGraph::Node* sink);

  size_t CountFusedNodesWithNewChild(IndexedForwardGraph::Node* child,
                                     IndexedForwardGraph::Node* dom_parent);

  // Initialize the groups.
  void InitGroups(const IndexedForwardGraph& graph);

  // execute the fusion algorithm.
  void RunFuse(const IndexedForwardGraph& graph, const DominatorTree& post_dom_tree, int phase);
};

}  // namespace relay
}  // namespace ostar
#endif  // OSTAR_RELAY_ANALYSIS_GRAPH_PARTITIONER_H_
