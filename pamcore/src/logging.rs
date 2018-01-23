use std::io;
use std::env;

use chrono;
use fern;
use log;

const DEBUG_LEVEL_KEY: &str = "PAMAGENT_LEVEL_LOG";

fn setup_logging(verbosity: u8) -> Result<(), fern::InitError> {
    let mut base_config = fern::Dispatch::new();

    base_config = match verbosity {
        0 => base_config
            .level(log::LevelFilter::Info)
            .level_for("overly-verbose-target", log::LevelFilter::Warn),
        1 => base_config
            .level(log::LevelFilter::Debug)
            .level_for("overly-verbose-target", log::LevelFilter::Info),
        2 => base_config.level(log::LevelFilter::Debug),
        _3_or_more => base_config.level(log::LevelFilter::Trace),
    };

    let stdout_config = fern::Dispatch::new()
        .format(|out, message, record| {
            out.finish(format_args!(
                "[{}][{}][{}] {}",
                chrono::Local::now().format("%Y-%m-%d %H:%M:%S%.f"),
                record.target(),
                record.level(),
                message
            ))
            //            }
        })
        .chain(io::stdout());

    base_config.chain(stdout_config).apply()?;

    Ok(())
}

pub fn configure_logging() {
    let debug_level: u8 = env::var(DEBUG_LEVEL_KEY)
        .unwrap_or("0".to_string())
        .parse()
        .unwrap_or(0);
    match setup_logging(debug_level) {
        Ok(_) => info!(target:"overly-verbose-target", "Logger successfully configured."),
        Err(e) => error!("Unable to configure logging. Error: {}", e),
    };
}
