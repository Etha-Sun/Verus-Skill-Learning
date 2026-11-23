//! For each file given on the command line, print one JSON line listing every
//! function with a body: name, mode, whether it returns a value, its attribute
//! paths, whether it sits inside a `verus!` block, and the exact span of the
//! signature start and of the body braces (1-based lines, 0-based char columns).
//! Files that do not parse are reported with "error" and no functions.

use quote::ToTokens;
use serde_json::{json, Value};
use std::str::FromStr;
use syn_verus::spanned::Spanned;
use syn_verus::{Attribute, Block, FnMode, ImplItem, Item, ReturnType, Signature, TraitItem};

fn pos(s: proc_macro2::LineColumn) -> Value {
    json!([s.line, s.column])
}

fn attrs(a: &[Attribute]) -> Vec<String> {
    a.iter().map(|x| x.to_token_stream().to_string()).collect()
}

fn record(out: &mut Vec<Value>, a: &[Attribute], sig: &Signature, block: &Block, in_verus: bool) {
    let mode = match &sig.mode {
        FnMode::Spec(_) | FnMode::SpecChecked(_) => "spec",
        FnMode::Proof(_) | FnMode::ProofAxiom(_) => "proof",
        _ => "exec",
    };
    let start = a.first().map(|x| x.span().start()).unwrap_or_else(|| sig.span().start());
    out.push(json!({
        "name": sig.ident.to_string(),
        "mode": mode,
        "returns": !matches!(sig.output, ReturnType::Default),
        "qualifiers": sig.constness.is_some() || sig.unsafety.is_some() || sig.asyncness.is_some() || sig.abi.is_some(),
        "attrs": attrs(a),
        "in_verus": in_verus,
        "item_start": pos(start),
        "body_start": pos(block.span().start()),
        "body_end": pos(block.span().end()),
    }));
}

fn visit(items: &[Item], in_verus: bool, out: &mut Vec<Value>) {
    for item in items {
        match item {
            Item::Fn(f) => record(out, &f.attrs, &f.sig, &f.block, in_verus),
            Item::Impl(i) => {
                for ii in &i.items {
                    if let ImplItem::Fn(f) = ii {
                        record(out, &f.attrs, &f.sig, &f.block, in_verus);
                    }
                }
            }
            Item::Trait(t) => {
                for ti in &t.items {
                    if let TraitItem::Fn(f) = ti {
                        if let Some(b) = &f.default {
                            record(out, &f.attrs, &f.sig, b, in_verus);
                        }
                    }
                }
            }
            Item::Mod(m) => {
                if let Some((_, inner)) = &m.content {
                    visit(inner, in_verus, out);
                }
            }
            Item::Macro(m) if m.mac.path.is_ident("verus") => {
                if let Ok(f) = syn_verus::parse2::<syn_verus::File>(m.mac.tokens.clone()) {
                    visit(&f.items, true, out);
                }
            }
            _ => {}
        }
    }
}

fn main() {
    for path in std::env::args().skip(1) {
        let code = std::fs::read_to_string(&path).unwrap_or_default();
        let parsed = proc_macro2::TokenStream::from_str(&code)
            .map_err(|e| e.to_string())
            .and_then(|ts| syn_verus::parse2::<syn_verus::File>(ts).map_err(|e| e.to_string()));
        let line = match parsed {
            Ok(file) => {
                let mut fns = Vec::new();
                visit(&file.items, false, &mut fns);
                json!({"file": path, "functions": fns})
            }
            Err(e) => json!({"file": path, "error": e, "functions": []}),
        };
        println!("{}", line);
    }
}
