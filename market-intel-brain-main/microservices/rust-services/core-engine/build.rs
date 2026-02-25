fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Compile protobuf files
    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .out_dir("src/proto")
        .compile(
            &[
                "microservices/proto/versions/v1/common.proto",
                "microservices/proto/versions/v1/core_engine.proto",
                "microservices/proto/versions/v1/analytics.proto",
            ],
            &["microservices/proto/versions/v1"],
        )?;
    Ok(())
}
