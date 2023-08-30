#ifndef OSTAR_DRIVER_INTERNAL_DRIVER_API_H_
#define OSTAR_DRIVER_INTERNAL_DRIVER_API_H_

#include <ostar/ir/module.h>
#include <ostar/target/target.h>

namespace ostar {
runtime::Module TIRToRuntime(const Map<Target, IRModule>& input, const Target& target_host);

}  // namespace ostar

#endif 
