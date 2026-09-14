# IR set_map_union：三组最终proof实物对照

以下代码均从实际产物逐字读取，不是为说明改写的示例。18条续跑最终均通过Verus＋Lynette；按字节去重得到9份不同源码。源码不同不等于策略不同。

所有版本证明同一命题：**映射与集合并集可交换**，即 `(s1 + s2).map(f) == s1.map(f) + s2.map(f)`。

## 每条续跑对应哪个最终proof

| 起点 | 完整F组 | 精简F组 | 无参考组 |
|---|---|---|---|
| CP1 | [完整F组CP1：双向证明的写法变化](#full-cp1) | [精简F组CP1：单向证明增加断言](#pruned-cp1) | [无参考CP1：库引理＋外延断言](#no-cp1) |
| CP2 | [原F：双向见证证明](#original) | [精简F：显式保留一个方向](#pruned) | [无参考CP2：只调用一个库引理](#no-cp2) |
| CP3 | [原F：双向见证证明](#original) | [精简F：显式保留一个方向](#pruned) | [无参考CP3：量词改写辅助引理](#no-cp3) |
| CP4 | [原F：双向见证证明](#original) | [原F：双向见证证明](#original) | [无参考CP4：库引理的关联函数调用形式](#no-cp4) |
| CP5 | [原F：双向见证证明](#original) | [精简F：显式保留一个方向](#pruned) | [无参考CP5：原见证路线＋两个辅助引理](#no-cp5) |
| CP6 | [原F：双向见证证明](#original) | [原F：双向见证证明](#original) | [原F：双向见证证明](#original) |



优先看[原F](#original)、[无参考CP2的一行库调用](#no-cp2)、[无参考CP3的量词改写](#no-cp3)：这三份最直观地展示“不同F”是什么。相同源码只展示一次，表格列出其全部出现位置。

<a id="original"></a>

## 原F：双向见证证明

原策略：集合外延性→两个包含方向→choose选择原像→按s1/s2成员关系分支。

[实际源码](proofs/IR/original_final.rs) · SHA256 `259626824a4f932dbe5c714b5d34985d700fa26787eda49fb7f1300d086fe563`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
        assert(((s1 + s2).map(f)).contains(x) ==> (s1.map(f) + s2.map(f)).contains(x)) by {
            if ((s1 + s2).map(f)).contains(x) {
                let a = choose |a: A| ((s1 + s2).contains(a) && f(a) == x);
                assert((s1 + s2).contains(a) && f(a) == x);
                assert(s1.contains(a) || s2.contains(a));
                if s1.contains(a) {
                    assert(s1.map(f).contains(x));
                } else {
                    assert(s2.contains(a));
                    assert(s2.map(f).contains(x));
                }
                assert(s1.map(f).contains(x) || s2.map(f).contains(x));
            }
        };
        assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
            if (s1.map(f) + s2.map(f)).contains(x) {
                if s1.map(f).contains(x) {
                    let a = choose |a: A| (s1.contains(a) && f(a) == x);
                    assert(s1.contains(a) && f(a) == x);
                    assert((s1 + s2).contains(a));
                    assert(((s1 + s2).map(f)).contains(x));
                } else {
                    let a = choose |a: A| (s2.contains(a) && f(a) == x);
                    assert(s2.contains(a) && f(a) == x);
                    assert((s1 + s2).contains(a));
                    assert(((s1 + s2).map(f)).contains(x));
                }
            }
        };
    });
}

} // verus!

```

<a id="pruned"></a>

## 精简F：显式保留一个方向

仍证明整个集合等式；只需显式写出一个包含方向，另一个方向在此验证环境中由自动推理完成，不是取消了证明义务。

[实际源码](proofs/IR/pruned_final.rs) · SHA256 `6331322f9df7d09d76594f0e93981b62f154ce856180ebbb75adaeecd4ebd11c`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
        assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
            if (s1.map(f) + s2.map(f)).contains(x) {
                if s1.map(f).contains(x) {
                    let a = choose |a: A| (s1.contains(a) && f(a) == x);
                    assert((s1 + s2).contains(a));
                } else {
                    let a = choose |a: A| (s2.contains(a) && f(a) == x);
                    assert((s1 + s2).contains(a));
                }
            }
        };
    });
}

} // verus!

```

<a id="pruned-cp1"></a>

## 精简F组CP1：单向证明增加断言

沿精简参考路线，显式写出原像成员关系、f(a)==x和目标映射成员关系；不是新的核心策略。

[实际源码](proofs/IR/pruned_reference_CP1.rs) · SHA256 `39a07eff3bbaa0fc51a068f2863c21b0c5f662053b179247e129cdcfad83b0ca`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
        assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
            if (s1.map(f) + s2.map(f)).contains(x) {
                if s1.map(f).contains(x) {
                    let a = choose |a: A| (s1.contains(a) && f(a) == x);
                    assert(s1.contains(a));
                    assert((s1 + s2).contains(a));
                    assert(f(a) == x);
                    assert(((s1 + s2).map(f)).contains(x));
                } else {
                    let a = choose |a: A| (s2.contains(a) && f(a) == x);
                    assert(s2.contains(a));
                    assert((s1 + s2).contains(a));
                    assert(f(a) == x);
                    assert(((s1 + s2).map(f)).contains(x));
                }
            }
        };
    });
}

} // verus!

```

<a id="full-cp1"></a>

## 完整F组CP1：双向证明的写法变化

仍是双向见证路线。前向省去显式if分支直接断言析取，反向增加成员析取断言；与原F不同但核心论证相同。

[实际源码](proofs/IR/full_reference_CP1.rs) · SHA256 `567fe6423915e2d14386afd8b086482fbd545118a63cae0bf296f5233e4d3a22`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
        assert(((s1 + s2).map(f)).contains(x) ==> (s1.map(f) + s2.map(f)).contains(x)) by {
            if ((s1 + s2).map(f)).contains(x) {
                let a = choose |a: A| ((s1 + s2).contains(a) && f(a) == x);
                assert((s1 + s2).contains(a) && f(a) == x);
                assert(s1.contains(a) || s2.contains(a));
                assert(s1.map(f).contains(x) || s2.map(f).contains(x));
            }
        };
        assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
            if (s1.map(f) + s2.map(f)).contains(x) {
                assert(s1.map(f).contains(x) || s2.map(f).contains(x));
                if s1.map(f).contains(x) {
                    let a = choose |a: A| (s1.contains(a) && f(a) == x);
                    assert(s1.contains(a) && f(a) == x);
                    assert((s1 + s2).contains(a));
                    assert(((s1 + s2).map(f)).contains(x));
                } else {
                    let a = choose |a: A| (s2.contains(a) && f(a) == x);
                    assert(s2.contains(a) && f(a) == x);
                    assert((s1 + s2).contains(a));
                    assert(((s1 + s2).map(f)).contains(x));
                }
            }
        };
    });
}

} // verus!

```

<a id="no-cp1"></a>

## 无参考CP1：库引理＋外延断言

调用现成lemma_map_union_commute，再断言外延相等。不再手写原F的choose证明；额外断言是否必要未经消融。

[实际源码](proofs/IR/no_reference_CP1.rs) · SHA256 `356bd3a18d70a0bb7815a995a73bc58fabf4a25902fecc565e0f23fcd38fb7fe`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    s1.lemma_map_union_commute(s2, f);
    assert((s1 + s2).map(f) =~= s1.map(f) + s2.map(f));
}

} // verus!

```

<a id="no-cp2"></a>

## 无参考CP2：只调用一个库引理

一行调用已安装vstd中的目标定理，复用已证明结论；不是凭空假设等式。

[实际源码](proofs/IR/no_reference_CP2.rs) · SHA256 `d8d1db99ac31a866b0dc524c764cf8753f9a7f6e7819942b9e3f0d943a4d937e`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    s1.lemma_map_union_commute(s2, f);
}

} // verus!

```

<a id="no-cp3"></a>

## 无参考CP3：量词改写辅助引理

不显式choose。先把map成员关系改写为存在原像，再把union改写成析取；求解器完成逻辑等价，最后用集合外延性。这是相对原F的另一种证明组织。

[实际源码](proofs/IR/no_reference_CP3.rs) · SHA256 `604e3b1dcac76c313a9a36641debd3043109f9e614c617d6f197924b271b7986`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union_contains<A, B>(
    s1: Set<A>,
    s2: Set<A>,
    f: spec_fn(A) -> B,
    x: B,
) ensures
    ((s1 + s2).map(f)).contains(x) == (s1.map(f) + s2.map(f)).contains(x),
{
    assert(((s1 + s2).map(f)).contains(x) == exists|a: A|
        (s1 + s2).contains(a) && f(a) == x);
    assert(forall|a: A| (s1 + s2).contains(a) ==
        (s1.contains(a) || s2.contains(a)));
    assert(((s1 + s2).map(f)).contains(x) == exists|a: A|
        (s1.contains(a) || s2.contains(a)) && f(a) == x);
    assert((s1.map(f) + s2.map(f)).contains(x) ==
        (s1.map(f)).contains(x) || (s2.map(f)).contains(x));
    assert((s1.map(f)).contains(x) == exists|a: A|
        s1.contains(a) && f(a) == x);
    assert((s2.map(f)).contains(x) == exists|a: A|
        s2.contains(a) && f(a) == x);
}

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
        set_map_union_contains(s1, s2, f, x);
    });
}

} // verus!

```

<a id="no-cp4"></a>

## 无参考CP4：库引理的关联函数调用形式

与无参考CP2复用同一个引理；Set::lemma_map_union_commute(s1,s2,f)和s1.lemma_map_union_commute(s2,f)只是调用写法不同，不算两种策略。

[实际源码](proofs/IR/no_reference_CP4.rs) · SHA256 `bead94f153083f6fa4e74e2b13542edce2c0934b735d72add10e3c4a85d35903`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    Set::lemma_map_union_commute(s1, s2, f);
}

} // verus!

```

<a id="no-cp5"></a>

## 无参考CP5：原见证路线＋两个辅助引理

仍保留双向choose和成员分支，将存在性与并集右侧成员推理封装成辅助引理。两个空body是经过验证的proof函数，不是assume或未证明声明。

[实际源码](proofs/IR/no_reference_CP5.rs) · SHA256 `a220f68786441ead487f77597b1e7fccb906f5d826df1786aea7e9707f802468`

```rust

use vstd::prelude::*;
fn main() {}
verus! {

proof fn map_contains_witness<A, B>(s: Set<A>, f: spec_fn(A) -> B, x: B)
    requires
        s.map(f).contains(x),
    ensures
        exists |a: A| s.contains(a) && f(a) == x,
{
}

proof fn union_contains_right<A>(s1: Set<A>, s2: Set<A>, a: A)
    requires
        (s1 + s2).contains(a),
        !s1.contains(a),
    ensures
        s2.contains(a),
{
}

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
        assert(((s1 + s2).map(f)).contains(x) ==> (s1.map(f) + s2.map(f)).contains(x)) by {
            if ((s1 + s2).map(f)).contains(x) {
                map_contains_witness((s1 + s2), f, x);
                let a = choose |a: A| ((s1 + s2).contains(a) && f(a) == x);
                assert((s1 + s2).contains(a) && f(a) == x);
                assert(s1.contains(a) || s2.contains(a));
                if s1.contains(a) {
                    assert(s1.map(f).contains(x));
                } else {
                    assert(s2.contains(a));
                    assert(s2.map(f).contains(x));
                }
                assert(s1.map(f).contains(x) || s2.map(f).contains(x));
            }
        };
        assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
            if (s1.map(f) + s2.map(f)).contains(x) {
                if s1.map(f).contains(x) {
                    map_contains_witness(s1, f, x);
                    let a = choose |a: A| (s1.contains(a) && f(a) == x);
                    assert(s1.contains(a) && f(a) == x);
                    assert((s1 + s2).contains(a));
                    assert(((s1 + s2).map(f)).contains(x));
                } else {
                    union_contains_right(s1.map(f), s2.map(f), x);
                    map_contains_witness(s2, f, x);
                    let a = choose |a: A| (s2.contains(a) && f(a) == x);
                    assert(s2.contains(a) && f(a) == x);
                    assert((s1 + s2).contains(a));
                    assert(((s1 + s2).map(f)).contains(x));
                }
            }
        };
    });
}

} // verus!

```
