# altdatahub C++ SDK

中国人民银行征信中心「金融信用信息基础数据库替代数据通」的第三方 C++ SDK
（**非官方**，与征信中心无隶属关系）。

**这是一个 header-only 薄封装，直接复用 [`sdks/c/`](../c/README.md) 的 C 库。**

## 为什么不做「独立 C++ SDK」

仓库其它六种 SDK 各自带一套 51+12 个模型（`tools/gen_code.py` 生成）、报文组装、
错误码表和信封解包，再各自跑一遍 `contract/vectors.json`。如果 C++ 也照抄一遍：

- `tools/gen_code.py` 要新增 C++ 产物，`gen_code.py --check` 多一个文件
- 51+12 个模型要再维护一份
- 报文/错误码/信封的契约向量要再写一遍，等于同一份行为维护两处

而 C 库已经把这三层做完了。C++ 真正缺的只是**惯用接口**：RAII、异常、
`std::string` / `std::vector` / `std::map`、按大类的方法。所以这里只补这层，
用 `extern "C"` 包裹 C 头文件，**不改 C SDK 一行代码、不动生成器、不改任何生成物**。

C 头文件本身没有 `__cplusplus` 守卫，所以 `#include` 必须包在 `extern "C" { }` 里
（本 SDK 的 `altdatahub.hpp` 已经做好了）。

## 依赖与构建

- C++17 标准库
- `sdks/c/build/libaltdatahub.a`（Makefile 会自动调用 `make -C ../c all` 构建）
- 系统：`libcurl4-openssl-dev`、`make`、`g++`

```bash
cd sdks/cpp
make test          # 自动构建 C 静态库 → 编译测试 → 运行，退出码即结论

# CI 同款消毒器构建（C 库与 C++ 必须同时带 sanitizer）
cd ../c && make clean && ASAN_OPTIONS=detect_leaks=0 make test CFLAGS="-std=c11 -Wall -Wextra -Wpedantic -g -fsanitize=address,undefined -fno-omit-frame-pointer"
cd ../cpp && make clean && ASAN_OPTIONS=detect_leaks=0 make test CXXFLAGS="-std=c++17 -Wall -Wextra -Wpedantic -g -fsanitize=address,undefined -fno-omit-frame-pointer"
```

Debian/Ubuntu：`apt-get install -y make g++ pkg-config libcurl4-openssl-dev`

## 用法

```cpp
#include "altdatahub.hpp"
#include <iostream>

int main() {
    try {
        altdatahub::Client client = altdatahub::Client::from_env();  // 读 EDS_* 环境变量
        altdatahub::Rows rows = client.query("S0101", {{"entName", "贵州茅台"}});
        for (const auto& row : rows) {
            auto it = row.find("entName");
            if (it != row.end()) std::cout << it->second << "\n";
        }
    } catch (const altdatahub::Error& e) {
        std::cerr << e.what() << " (retryable=" << e.retryable() << ")\n";
        return 1;
    }
}
```

编译：`g++ -std=c++17 -Iinclude -I../c/include example.cpp ../c/build/libaltdatahub.a $(pkg-config --libs libcurl) -o example`

## API

| 类型 | 说明 |
|---|---|
| `altdatahub::Error` | 继承 `std::runtime_error`，接管并释放 C 侧 `ad_error`；带 `kind()` / `status()` / `retryable()` / `code()` / `category()` |
| `altdatahub::Config` | `from_env()` / `from_map(map)`；`service_code(code)` 返回 `std::string`；`to_string()` 是脱敏自述（account 显示 `***`） |
| `altdatahub::Client` | `from_env()` 真实传输；`from_transport(ad_transport*)` 离线注入（所有权仍归调用方）；`pending()` 显式失败 |
| `query` / `query_in` | `query(code, params)` 按 productCode 自动反查大类；`query_in(category, code, params)` 显式校验归属 |
| 10 个大类方法 | `enterprise_basic` / `market_supervision` / `judicial` / `intellectual_property` / `stock` / `bond` / `administration` / `honor` / `operation` / `finance` |
| `Params` / `Row` / `Rows` | `std::map<std::string,std::string>` / `std::vector<Row>` |

## 所有权与线程安全

`Client` 内部按 `config → transport → client` 顺序构造，`unique_ptr` 成员按声明**逆序**
析构，保证被 transport 借用的 config 最后释放；移动构造/赋值可用，拷贝被禁用。
单个 `Client` 不保证并发安全，每个线程各建一个即可。

## 契约向量

报文形状 / 错误码判定 / 响应信封解包三组跨语言向量由
[`sdks/c/tests/test_contract_vectors.c`](../c/tests/test_contract_vectors.c) 覆盖 ——
C++ 层不重写这三层行为，因此不重复维护一份断言。

CI 的 `ci-cpp-sdk` job **同时跑 C 与 C++ 的测试**（含 ASan/UBSan），
所以改了 C 库或 C++ 封装，向量验证都不会被绕过。C++ 自身的测试聚焦
RAII、异常、标准容器转换与 10 个大类路由，用离线 `ad_transport` 注入，完全不联网。
