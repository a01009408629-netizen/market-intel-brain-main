fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Compile protobuf files
    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .out_dir("src/proto")
        .compile(
            &[
                "../../proto/common.proto",
                "../../proto/core_engine.proto",
            ],
            &["../../proto"],
        )?;
    Ok(())
}
