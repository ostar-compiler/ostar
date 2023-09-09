#include <ostar/driver/driver_api.h>
#include <ostar/ir/expr.h>
#include <ostar/ir/memory_pools.h>
#include <ostar/relay/analysis.h>
#include <ostar/relay/executor.h>
#include <ostar/relay/expr.h>
#include <ostar/relay/qnn/transform.h>
#include <ostar/relay/runtime.h>
#include <ostar/relay/transform.h>
#include <ostar/runtime/device_api.h>
#include <ostar/target/compilation_config.h>

#include <memory>

#include "../../driver/internal_driver_api.h"
#include "../../target/func_registry_generator.h"
#include "../../target/metadata_module.h"
#include "../../target/source/codegen_source_base.h"
#include "te_compiler.h"
#include "utils.h"

namespace ostar {
namespace relay {
namespace transform {
Pass LabelOps();
}
namespace backend {

using namespace ostar::relay::transform;

struct BuildOutput {
  std::string graph_json;
  runtime::Module mod;
  std::unordered_map<std::string, ostar::runtime::NDArray> params;
};

struct ExecutorCodegen {
  void Init(runtime::Module* m, const Array<Target>& raw_targets) {
    CallFunc("init", m, raw_targets);
  }

  void Codegen(IRModule mod, const Function& func, String mod_name) {
    CallFunc("codegen", mod, func, mod_name);
  }

  virtual void UpdateOutput(BuildOutput* ret) = 0;

  Map<String, FunctionInfo> GetFunctionMetadata() {
    return CallFunc<Map<String, FunctionInfo>>("get_function_metadata", nullptr);
  }

  std::unordered_map<std::string, ostar::runtime::NDArray> GetParams() {
    std::unordered_map<std::string, ostar::runtime::NDArray> ret;
    auto names = CallFunc<Array<runtime::String>>("list_params_name", nullptr);
    for (const auto& expr : names) {
      std::string key = expr;
      ret[key] = CallFunc<runtime::NDArray>("get_param_by_name", key);
    }
    return ret;
  }

  Array<ostar::runtime::Module> GetExternalModules() {
    return CallFunc<Array<ostar::runtime::Module>>("get_external_modules", nullptr);
  }

  Map<Target, IRModule> GetIRModule() {
    return CallFunc<Map<Target, IRModule>>("get_irmodule", nullptr);
  }

  Array<String> ListDevices() { return CallFunc<Array<String>>("get_devices"); }

  relay::backend::ExecutorCodegenMetadata GetExecutorCodegenMetadata() {
    return CallFunc<relay::backend::ExecutorCodegenMetadata>("get_executor_codegen_metadata");
  }
  virtual ~ExecutorCodegen() {}

 protected:
  ostar::runtime::Module mod;
  template <typename R, typename... Args>
  R CallFunc(const std::string& name, Args... args) {
    auto pf = mod.GetFunction(name, false);
    return pf(std::forward<Args>(args)...);
  }
  template <typename... Args>
  void CallFunc(const std::string& name, Args... args) {
    auto pf = mod.GetFunction(name, false);
    pf(std::forward<Args>(args)...);
    return;
  }
};

struct AOTCodegen : ExecutorCodegen {
  AOTCodegen() {
    auto pf = GetPackedFunc("relay.build_module._AOTExecutorCodegen");
    mod = (*pf)();
  }

  void UpdateOutput(BuildOutput* ret) override { ret->graph_json = ""; }

  ~AOTCodegen() {}
};

struct GraphCodegen : ExecutorCodegen {
  GraphCodegen() {
    auto pf = GetPackedFunc("relay.build_module._GraphExecutorCodegen");
    mod = (*pf)();
  }
  void UpdateOutput(BuildOutput* ret) override { ret->graph_json = GetGraphJSON(); }

  std::string GetGraphJSON() { return CallFunc<std::string>("get_graph_json", nullptr); }

  ~GraphCodegen() {}
};

std::unique_ptr<ExecutorCodegen> MakeExecutorCodegen(String executor_str) {
  std::unique_ptr<ExecutorCodegen> ret;
  if (executor_str == runtime::kostarExecutorGraph) {
    ret = std::make_unique<GraphCodegen>();
  } else if (executor_str == runtime::kostarExecutorAot) {
    ret = std::make_unique<AOTCodegen>();
  } else {
    CHECK(false) << "Executor " << executor_str << " not supported";
  }
  return ret;
}
class RelayBuildModule : public runtime::ModuleNode {
 public:
  RelayBuildModule() = default;

  PackedFunc GetFunction(const String& name, const ObjectPtr<Object>& sptr_to_self) final {
    if (name == "get_graph_json") {
      return PackedFunc(
          [sptr_to_self, this](ostarArgs args, ostarRetValue* rv) { *rv = this->GetGraphJSON(); });
    } else if (name == "get_module") {
      return PackedFunc(
          [sptr_to_self, this](ostarArgs args, ostarRetValue* rv) { *rv = this->GetModule(); });
    } else if (name == "build") {
      return PackedFunc([sptr_to_self, this](ostarArgs args, ostarRetValue* rv) {
        ICHECK_EQ(args.num_args, 8);
        this->Build(args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7]);
      });
    } else if (name == "list_params") {
      return PackedFunc(
          [sptr_to_self, this](ostarArgs args, ostarRetValue* rv) { *rv = this->ListParamNames(); });
    } else if (name == "get_params") {
      return PackedFunc(
          [sptr_to_self, this](ostarArgs args, ostarRetValue* rv) { *rv = this->GetParams(); });
    } else if (name == "set_params") {
      return PackedFunc([sptr_to_self, this](ostarArgs args, ostarRetValue* rv) {
        Map<String, Constant> params = args[0];
        for (const auto& kv : params) {
          this->SetParam(kv.first, kv.second->data);
        }
      });
    } else if (name == "get_devices") {
      return PackedFunc([sptr_to_self, this](ostarArgs args, ostarRetValue* rv) {
        *rv = this->executor_codegen_->ListDevices();
      });
    } else if (name == "get_irmodule") {
      return PackedFunc([sptr_to_self, this](ostarArgs args, ostarRetValue* rv) {
        *rv = this->executor_codegen_->GetIRModule();
      });
    } else if (name == "get_external_modules") {
      return PackedFunc([sptr_to_self, this](ostarArgs args, ostarRetValue* rv) {
        *rv = this->executor_codegen_->GetExternalModules();
      });
    } else if (name == "get_function_metadata") {
      return PackedFunc([sptr_to_self, this](ostarArgs args, ostarRetValue* rv) {
        *rv = this->executor_codegen_->GetFunctionMetadata();
      });
    } else if (name == "get_executor_codegen_metadata") {
      return PackedFunc([sptr_to_self, this](ostarArgs args, ostarRetValue* rv) {
        *rv = this->executor_codegen_->GetExecutorCodegenMetadata();
      });
    } else if (name == "optimize") {
      return PackedFunc([sptr_to_self, this](ostarArgs args, ostarRetValue* rv) {
        ICHECK_EQ(args.num_args, 2);
        *rv = this->Optimize(args[0], args[1]);
      });
    } else {
      LOG(FATAL) << "Unknown packed function: " << name;
      return PackedFunc([sptr_to_self, name](ostarArgs args, ostarRetValue* rv) {});
    }
  }

  const std::string& GetGraphJSON() { return ret_.graph_json; }

  runtime::Module GetModule() { return ret_.mod; }

  Array<runtime::String> ListParamNames() {
    Array<runtime::String> ret;
    for (const auto& kv : params_) {
      ret.push_back(kv.first);
    }
    return ret;
  }

  Map<String, Constant> GetParams() {
    Map<String, Constant> ret;
    for (const auto& kv : ret_.params) {
      ret.Set(kv.first, Constant(kv.second));
    }
    return ret;
  }

  void SetParam(const std::string& name, runtime::NDArray data_in) { params_[name] = data_in; }

  const char* type_key() const final { return "RelayBuildModule"; }

  int GetPropertyMask() const final { return runtime::ModulePropertyMask::kRunnable; }

  void Build(IRModule mod, const Array<Target>& raw_targets, const ostar::Target& target_host,
             const Executor& executor, const Runtime& runtime,
             const WorkspaceMemoryPools& workspace_memory_pools,
             const ConstantMemoryPools& constant_memory_pools, const String mod_name) {
    VLOG_CONTEXT << "Build";
    executor_ = executor;
    runtime_ = runtime;
    workspace_memory_pools_ = workspace_memory_pools;
    constant_memory_pools_ = constant_memory_pools;
    config_ = CompilationConfig(PassContext::Current(), raw_targets);
    VLOG(1) << "Using compilation config:" << std::endl << config_;
    BuildRelay(std::move(mod), mod_name);
  }

 protected:
  IRModule Optimize(IRModule relay_module, const Array<Target>& raw_targets) {
    VLOG_CONTEXT << "Optimize";
    config_ = CompilationConfig(PassContext ::Current(), raw_targets);
    VLOG(1) << "Using compilation config:" << std::endl << config_;
    return OptimizeImpl(std::move(relay_module));
  }

  IRModule OptimizeImpl(IRModule relay_module) {
    ICHECK(relay_module.defined()) << "The IRModule must be defined for the Relay compiler.";

    backend::BindParamsInModule(relay_module, params_);

    Array<Pass> pass_seqs =
        GetPassPrefix(/*is_homogenous=*/config_->primitive_targets.size() == 1, /*is_vm=*/false);
    transform::PassContext pass_ctx = PassContext::Current();

    if (config_->optional_homogeneous_target.defined()) {
      // This pass currently only supports the homogeneous case.
      pass_seqs.push_back(transform::SplitArgs(
          config_->optional_homogeneous_target->GetAttr<Integer>("max_function_args", 0)
              .value()
              .IntValue()));
    }

    pass_seqs.push_back(transform::PlanDevices(config_));

    pass_seqs.push_back(transform::FuseOps());

    transform::Pass seq = transform::Sequential(pass_seqs);
    if (config_->optional_homogeneous_target.defined()) {
      With<Target> tctx(config_->optional_homogeneous_target);
      relay_module = seq(relay_module);
    } else {
      relay_module = seq(relay_module);
    }

    // Do layout rewrite for auto-scheduler.
    if (backend::IsAutoSchedulerEnabled() && config_->optional_homogeneous_target.defined()) {
      Pass major_pass = transform::AutoSchedulerLayoutRewrite();
      bool enable_layout_rewrite_targets =
          config_->optional_homogeneous_target->GetTargetDeviceType() == kDLCPU ||
          config_->optional_homogeneous_target->GetAttr<String>("device", "") == "mali";
      if (enable_layout_rewrite_targets && pass_ctx.PassEnabled(major_pass->Info())) {
        With<Target> tctx(config_->optional_homogeneous_target);
        relay_module = major_pass(relay_module);
        relay_module = transform::DefuseOps()(relay_module);
        relay_module = transform::FoldConstant()(relay_module);
        relay_module = transform::FuseOps()(relay_module);
      }
    }
    if (backend::IsMetaScheduleEnabled() && config_->optional_homogeneous_target.defined()) {
      Pass major_pass = transform::MetaScheduleLayoutRewrite();
      bool enable_layout_rewrite_targets =
          config_->optional_homogeneous_target->GetTargetDeviceType() == kDLCPU ||
          config_->optional_homogeneous_target->GetAttr<String>("device", "") == "mali";
      if (enable_layout_rewrite_targets && pass_ctx.PassEnabled(major_pass->Info())) {
        With<Target> tctx(config_->optional_homogeneous_target);
        relay_module = major_pass(relay_module);
        relay_module = transform::DefuseOps()(relay_module);
        relay_module = transform::FoldConstant()(relay_module);
        relay_module = transform::FuseOps()(relay_module);
      }
    }

    relay_module = transform::InferType()(relay_module);
    relay_module = transform::Inline()(relay_module);
    relay_module = transform::InferType()(relay_module);
    relay_module = transform::LabelOps()(relay_module);
    relay_module = transform::AnnotateMemoryScope()(relay_module);

    ICHECK(relay_module.defined());

    return relay_module;
  }

  void BuildRelay(IRModule relay_module, const String& mod_name) {
    IRModule module = WithAttrs(
        relay_module, {{ostar::attr::kExecutor, executor_}, {ostar::attr::kRuntime, runtime_}});
    relay_module = OptimizeImpl(std::move(module));

    Function func = Downcast<Function>(relay_module->Lookup("main"));
    IRModule func_module = WithAttrs(IRModule::FromExpr(func),
                                     {{ostar::attr::kExecutor, executor_},
                                      {ostar::attr::kRuntime, runtime_},
                                      {ostar::attr::kWorkspaceMemoryPools, workspace_memory_pools_},
                                      {ostar::attr::kConstantMemoryPools, constant_memory_pools_}});

    // Generate code for the updated function.
    executor_codegen_ = MakeExecutorCodegen(executor_->name);
    executor_codegen_->Init(nullptr, config_->primitive_targets);
    executor_codegen_->Codegen(func_module, func, mod_name);
    executor_codegen_->UpdateOutput(&ret_);
    ret_.params = executor_codegen_->GetParams();

    auto lowered_funcs = executor_codegen_->GetIRModule();

    Target ext_dev("ext_dev");
    if (lowered_funcs.find(ext_dev) != lowered_funcs.end()) {
      lowered_funcs.Set(ext_dev, IRModule());
    }

    const Target& host_target = config_->host_virtual_device->target;
    const runtime::PackedFunc* pf = runtime::Registry::Get("codegen.LLVMModuleCreate");
    if (lowered_funcs.size() == 0) {
      if (host_target->kind->name == "llvm") {
        CHECK(pf != nullptr) << "Unable to create empty module for llvm without llvm codegen.";
        ret_.mod = (*pf)(host_target->str(), "empty_module");
      } else {
        ret_.mod = ostar::codegen::CSourceModuleCreate(";", "", Array<String>{});
      }
    } else {
      ret_.mod = ostar::TIRToRuntime(lowered_funcs, host_target);
    }

    auto ext_mods = executor_codegen_->GetExternalModules();
    ret_.mod = ostar::codegen::CreateMetadataModule(ret_.params, ret_.mod, ext_mods, host_target,
                                                  runtime_, executor_,
                                                  executor_codegen_->GetExecutorCodegenMetadata());
    // Remove external params which were stored in metadata module.
    for (ostar::runtime::Module mod : ext_mods) {
      auto pf_var = mod.GetFunction("get_const_vars");
      if (pf_var != nullptr) {
        Array<String> variables = pf_var();
        for (size_t i = 0; i < variables.size(); i++) {
          auto it = ret_.params.find(variables[i].operator std::string());
          if (it != ret_.params.end()) {
            VLOG(1) << "constant '" << variables[i] << "' has been captured in external module";
            ret_.params.erase(it);
          }
        }
      }
    }
  }

 protected:
  std::unique_ptr<ExecutorCodegen> executor_codegen_;
  Executor executor_;
  Runtime runtime_;
  WorkspaceMemoryPools workspace_memory_pools_;
  ConstantMemoryPools constant_memory_pools_;
  std::unordered_map<std::string, runtime::NDArray> params_;
  BuildOutput ret_;
  CompilationConfig config_;
};

runtime::Module RelayBuildCreate() {
  auto exec = make_object<RelayBuildModule>();
  return runtime::Module(exec);
}

ostar_REGISTER_GLOBAL("relay.build_module._BuildModule").set_body([](ostarArgs args, ostarRetValue* rv) {
  *rv = RelayBuildCreate();
});

ostar_REGISTER_GLOBAL("relay.build_module.BindParamsByName")
    .set_body([](ostarArgs args, ostarRetValue* rv) {
      Map<String, Constant> params = args[1];
      std::unordered_map<std::string, runtime::NDArray> params_;
      for (const auto& kv : params) {
        params_[kv.first] = kv.second->data;
      }
      *rv = relay::backend::BindParamsByName(args[0], params_);
    });

}  
}  
} 
