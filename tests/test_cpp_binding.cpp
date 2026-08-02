#include "bindings/cpp/nlsql.hpp"
#include <cassert>
#include <stdexcept>

int main() {
    nlsqlc::Context context;
    nlsql_compile_request bad{"(nlsql 1 (query", nullptr, nullptr, NLSQL_DIALECT_POSTGRES, nullptr};
    for (int i = 0; i < 1000; ++i) {
        try {
            (void)nlsqlc::compile_ir(context, bad);
            return 2;
        } catch (const std::runtime_error &) {
        }
    }
    return 0;
}
