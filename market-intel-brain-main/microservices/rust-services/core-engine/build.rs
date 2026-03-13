use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // CARGO_MANIFEST_DIR = /app/microservices/rust-services/core-engine (inside Docker)
    let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());

    // Go up 3 levels to reach the build context root (/app inside Docker)
    let root = manifest_dir
        .parent().unwrap()  // rust-services
        .parent().unwrap()  // microservices
        .parent().unwrap(); // /app (build context root)

    let proto_dir = root.join("microservices/proto/versions/v1");

    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        // Do NOT set out_dir — let tonic use the standard OUT_DIR
        // so that tonic::include_proto! can find the generated files
        .compile(
            &[
                proto_dir.join("common.proto").to_str().unwrap(),
                proto_dir.join("core_engine.proto").to_str().unwrap(),
                proto_dir.join("analytics.proto").to_str().unwrap(),
            ],
            &[proto_dir.to_str().unwrap()],
        )?;

    Ok(())
}
