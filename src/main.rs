//! LombokSimHash CLI tool.

use lomboksimhash::sha256::to_hex;
use lomboksimhash::{hamming64, sha256, simhash64_text};

fn print_usage() {
    eprintln!("LombokSimHash CLI v0.1.0");
    eprintln!();
    eprintln!("Usage:");
    eprintln!("  lomboksimhash-cli simhash <text>        Compute SimHash64 of text");
    eprintln!("  lomboksimhash-cli sha256 <text>         Compute SHA-256 of text");
    eprintln!("  lomboksimhash-cli compare <text1> <text2>  Compare two texts (Hamming distance)");
    eprintln!();
    eprintln!("Part of LombokRAGFrameworks — https://github.com/codinglombok/LombokRAGFrameworks");
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() < 2 {
        print_usage();
        std::process::exit(1);
    }

    match args[1].as_str() {
        "simhash" => {
            if args.len() < 3 {
                eprintln!("[ERR_ARGS] missing text argument");
                std::process::exit(1);
            }
            let text = &args[2];
            let hash = simhash64_text(text);
            println!("{:016x}", hash);
        }
        "sha256" => {
            if args.len() < 3 {
                eprintln!("[ERR_ARGS] missing text argument");
                std::process::exit(1);
            }
            let text = &args[2];
            let hash = sha256(text.as_bytes());
            println!("{}", to_hex(&hash));
        }
        "compare" => {
            if args.len() < 4 {
                eprintln!("[ERR_ARGS] need two text arguments");
                std::process::exit(1);
            }
            let h1 = simhash64_text(&args[2]);
            let h2 = simhash64_text(&args[3]);
            let dist = hamming64(h1, h2);
            println!("Text 1 SimHash: {:016x}", h1);
            println!("Text 2 SimHash: {:016x}", h2);
            println!("Hamming distance: {}", dist);
            println!("Similarity: {:.1}%", (1.0 - dist as f64 / 64.0) * 100.0);
        }
        "help" | "--help" | "-h" => {
            print_usage();
        }
        cmd => {
            eprintln!("[ERR_UNKNOWN_CMD] unknown command: {cmd}");
            print_usage();
            std::process::exit(1);
        }
    }
}
