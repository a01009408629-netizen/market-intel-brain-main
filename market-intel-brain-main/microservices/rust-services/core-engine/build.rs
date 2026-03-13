use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Use CARGO_MANIFEST_DIR to find proto files regardless of where cargo is invoked
    // Path: core-engine -> rust-services -> microservices -> market-intel-brain-main (root)
    let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let repo_root = manifest_dir
        .parent().unwrap()  // rust-services
        .parent().unwrap()  // microservices
        .parent().unwrap(); // market-intel-brain-main root

    let proto_dir = repo_root.join("microservices/proto/versions/v1");
    let out_dir = manifest_dir.join("src/proto");

    // Create output directory if it doesn't exist
    std::fs::create_dir_all(&out_dir)?;

    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .out_dir(&out_dir)
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
