#pragma once
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include "nlsql/nlsql.h"

namespace nlsqlc {

inline void throw_status(nlsql_status status) {
    if (status != NLSQL_OK) throw std::runtime_error(nlsql_status_name(status));
}

class Context final {
public:
    explicit Context(const nlsql_config &config = {}) {
        throw_status(nlsql_context_create(&config, &context_));
    }
    ~Context() { nlsql_context_destroy(context_); }
    Context(const Context &) = delete;
    Context &operator=(const Context &) = delete;
    nlsql_context *get() const noexcept { return context_; }
private:
    nlsql_context *context_ = nullptr;
};

class Result final {
public:
    explicit Result(nlsql_compile_result *result) : result_(result) {}
    ~Result() { nlsql_compile_result_destroy(result_); }
    Result(const Result &) = delete;
    Result &operator=(const Result &) = delete;
    Result(Result &&other) noexcept : result_(std::exchange(other.result_, nullptr)) {}
    Result &operator=(Result &&other) noexcept {
        if (this != &other) {
            nlsql_compile_result_destroy(result_);
            result_ = std::exchange(other.result_, nullptr);
        }
        return *this;
    }
    nlsql_sql_view sql() const noexcept { return nlsql_result_sql(result_); }
    const char *canonical_ir() const noexcept { return nlsql_result_canonical_ir(result_); }
    const char *manifest() const noexcept { return nlsql_result_manifest(result_); }
    size_t parameter_count() const noexcept { return nlsql_result_param_count(result_); }
    uint64_t fingerprint() const noexcept { return nlsql_result_fingerprint(result_); }
    nlsql_compile_result *get() const noexcept { return result_; }
private:
    nlsql_compile_result *result_;
};

inline Result compile_ir(Context &context, const nlsql_compile_request &request) {
    nlsql_compile_result *result = nullptr;
    throw_status(nlsql_compile_ir(context.get(), &request, &result));
    return Result(result);
}

inline Result compile_set(Context &context, const nlsql_set_request &request) {
    nlsql_compile_result *result = nullptr;
    throw_status(nlsql_compile_set(context.get(), &request, &result));
    return Result(result);
}

} // namespace nlsqlc
