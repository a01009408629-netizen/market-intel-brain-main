use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());

    // CARGO_MANIFEST_DIR = /app/microservices/rust-services/core-engine
    // Go up 3 levels → /app (Docker build context root)
    let root = manifest_dir
        .parent().unwrap()  // rust-services
        .parent().unwrap()  // microservices
        .parent().unwrap(); // /app

    // ✅ include path = microservices/proto/
    //    so "versions/v1/common.proto" resolves correctly
    let proto_include = root.join("microservices/proto");
    let proto_dir    = root.join("microservices/proto/versions/v1");

    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        // ❌ NO custom out_dir — use cargo's OUT_DIR so include_proto! works
        .compile(
            &[
                proto_dir.join("common.proto")     .to_str().unwrap(),
                proto_dir.join("core_engine.proto").to_str().unwrap(),
            ],
            &[
                proto_include.to_str().unwrap(), // "versions/v1/common.proto"
                "/usr/include",                  // "google/protobuf/..."
            ],
        )?;

    Ok(())
}
