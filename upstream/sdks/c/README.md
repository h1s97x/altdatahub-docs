# altdatahub C SDK

中国人民银行征信中心「金融信用信息基础数据库替代数据通」的第三方 C SDK
（**非官方**，与征信中心无隶属关系）。

- **C11 标准库 + libcurl**，无其它依赖；JSON 解析与 51 个产品模型都在本仓内实现，
  不引第三方 JSON 库
- 10 个大类方法、`productCode` 枚举、错误契约、报文组装与响应解包
- 与 Python / TypeScript / Java / Go / C# / Rust 读**同一份**
  [`contract/vectors.json`](../../contract/vectors.json)
- 传输契约仍未与真实网关联调，见仓库根 [`docs/api/transport.md`](../../docs/api/transport.md)

## 构建与测试

```bash
cd sdks/c
make test          # 编译静态库 + 自跑测试，退出码即结论

# CI 同款消毒器构建
make clean
ASAN_OPTIONS=detect_leaks=0 make test CFLAGS="-std=c11 -Wall -Wextra -Wpedantic -g -fsanitize=address,undefined -fno-omit-frame-pointer"
```

`ASAN_OPTIONS=detect_leaks=0` 是因为 CI 的容器跑在 ptrace 之下，LeakSanitizer 在这种环境里
会直接 `LeakSanitizer has encountered a fatal error ... does not work under ptrace` 退出；
ASan/UBSan 本身不受影响。本地外跑可以去掉这个变量。

系统依赖（Debian/Ubuntu）：

```bash
apt-get install -y make gcc pkg-config libcurl4-openssl-dev
```

`make test` 的 cwd 是 `sdks/c/`；契约向量测试按 `../../contract/vectors.json` 定位文件，
**找不到文件时测试直接失败**（跨语言契约是硬约束，不允许静默跳过）。
测试拆成 `tests/test_main.c`（主体）与 `tests/test_contract_vectors.c`（向量），
共用 `tests/test_kit.h` 的断言宏；Makefile 自动编译 `tests/*.c`。

产物：`build/libaltdatahub.a`（静态库）、`build/test_main`（测试二进制），
均被 `.gitignore` 忽略。

## 公共头文件

| 头文件 | 内容 |
|---|---|
| `include/altdatahub.h` | 错误、配置、报文、大类、客户端、传输的主 API |
| `include/altdatahub_json.h` | 极简 JSON 树（数字按字面量文本保存，避免 18 位 ID 丢精度） |
| `include/altdatahub_types.h` | 51 + 12 个产品模型（由 `tools/gen_code.py` 生成，**勿手改**） |

## 最小示例

```c
#include "altdatahub.h"
#include <stdio.h>

int main(void) {
    ad_error *error = NULL;
    ad_config *config = ad_config_from_env(&error);   /* 读 EDS_* 环境变量 */
    if (config == NULL) {
        fprintf(stderr, "%s\n", error ? error->message : "配置失败");
        ad_error_free(error);
        return 1;
    }

    ad_transport *transport = ad_http_transport_new(config);
    ad_client *client = ad_client_new(transport);
    ad_json *params = ad_json_new_object();
    ad_json_object_set(params, "entName", ad_json_new_string("贵州茅台"));

    ad_rows *rows = ad_client_query_by_code(client, "S0101", params, &error);
    if (rows != NULL) {
        printf("返回 %zu 行\n", rows->count);
        ad_rows_free(rows);
    } else {
        fprintf(stderr, "%s\n", error ? error->message : "查询失败");
    }

    ad_json_free(params);
    ad_error_free(error);
    ad_client_free(client);
    ad_http_transport_free(transport);
    ad_config_free(config);   /* transport 只是借用，最后释放 */
    return 0;
}
```

链接：`cc example.c -Iinclude build/libaltdatahub.a $(pkg-config --libs libcurl) -o example`

## 内存约定

所有 `ad_*_new` / `*_from` / `*_parse` 返回的对象由调用方用对应的 `*_free` 释放；
`ad_error **` 出参在出错时被赋值，同样由调用方释放。
`ad_wire_build_payload` 深拷贝业务参数，不接管传入的 `params`；
`ad_wire_extract_rows` 返回新数组，调用方负责 `ad_json_free`。

## 契约向量

`tests/test_contract_vectors.c` 覆盖三组断言，与其它语言完全一致：

| 组 | 数量 | 校验内容 |
|---|---|---|
| `payload` | 4 | 8 个 `eds_*` 公共参数 + 业务参数同层平铺、`validDay` 覆盖、`eds_` 前缀拒绝 |
| `errors` | 7 | 业务码按值判定、`category` / `retryable`、业务数据里的 `xxxCode` 不误判 |
| `extract` | 9 | 5 种响应信封候选路径、顶层数组、空数组、找不到数据行时报错 |

改 `contract/vectors.json` 等于改契约，必须**所有语言同时跑通**。
