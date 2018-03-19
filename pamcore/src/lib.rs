//#![crate_type = "dylib"]
#![feature(proc_macro, specialization)]
#![feature(refcell_replace_swap)]
extern crate pyo3;
use pyo3::prelude::*;
extern crate backoff;
extern crate chrono;
extern crate fern;
#[macro_use]
extern crate lazy_static;
#[macro_use]
extern crate log;
extern crate rand;
#[macro_use]
extern crate serde_derive;
extern crate serde_json;
extern crate url;

use std::thread;

mod core;
mod output;
mod logging;
use core::{DatabaseNode, ExternalNode, FuncNode, StackNode, TransactionCache, CacheNode};
use url::Url;
use self::output::Output;
use self::output::PamCollectorOutput;

/// This module is implemented in Rust.
///
/// This module has the ability to configure the logging level
/// To configure the logging, it is necessary to set the variable environment PAMAGENT_LEVEL_LOG
/// with a value from 0 to 3 before the application starts, if the environment variable is not set
/// to the default value of 0 (see pamcore/src/logging.rs for more information)
///
#[py::modinit(pamagent_core)]
fn init(py: Python, m: &PyModule) -> PyResult<()> {
    logging::configure_logging();

    /// Set transaction
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :param str transaction: Transaction name.
    /// :param str path: Path of transaction. URI without qs as usual.
    /// :return: the return code.
    /// :rtype: bool
    ///
    #[pyfn(m, "set_transaction")]
    fn set_transaction_py(id: u64, transaction: String, path: Option<String>) -> PyResult<bool> {
        Ok(core::TRANSACTION_CACHE
            .write()
            .unwrap()
            .set_transaction(id, transaction, path))
    }

    /// Get transaction by id
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :return: Return transaction_id or None if Transaction not availability.
    /// :rtype: int or None
    ///
    #[pyfn(m, "get_transaction")]
    fn get_transaction_py(id: u64) -> PyResult<Option<u64>> {
        Ok(core::TRANSACTION_CACHE
            .read()
            .unwrap()
            .availability_transaction(id))
    }

    /// Get transaction start time
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :return: Return timestamp when Transaction started. If Transaction not found or Transaction
    ///          has empty stack (transaction not activate) return 0.0
    /// :rtype: float
    ///
    #[pyfn(m, "get_transaction_start_time")]
    fn get_transaction_start_time_py(id: u64) -> PyResult<f64> {
        Ok(core::TRANSACTION_CACHE
            .read()
            .unwrap()
            .get_transaction_start_time(id))
    }

    /// Get transaction end time
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :return: Return timestamp when Transaction ended. If Transaction not found or Transaction
    ///          has empty stack (transaction not activate) return 0.0
    /// :rtype: float
    ///
    #[pyfn(m, "get_transaction_end_time")]
    fn get_transaction_end_time_py(id: u64) -> PyResult<f64> {
        Ok(core::TRANSACTION_CACHE
            .read()
            .unwrap()
            .get_transaction_end_time(id))
    }

    /// Push trace node to current transaction
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :param int node_id: ID of TransactionNode. Object.__id__ as usual.
    /// :param float start_time: Timestamp when TransactionNode is activated
    /// :param func_name: Function name if exists
    /// :type func_name: str or None
    /// :return: the return code.
    /// :rtype: bool
    ///
    #[pyfn(m, "push_current")]
    fn push_current_py(
        id: u64,
        node_id: u64,
        start_time: f64,
        func_name: Option<String>,
    ) -> PyResult<bool> {
        Ok(core::TRANSACTION_CACHE.write().unwrap().push_current(
            id,
            StackNode::Func(FuncNode::new(
                node_id,
                start_time,
                func_name.unwrap_or_else(|| "unknow".to_string()),
            )),
        ))
    }

    /// Push external trace node to current transaction
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :param int node_id: ID of TransactionNode. Object.__id__ as usual.
    /// :param float start_time: Timestamp when TransactionNode is activated
    /// :param str url: Full URL that was used to request an external service.
    /// :param str library: Name of library
    /// :param str method: Method that was used to request an external service
    /// :return: the return code.
    /// :rtype: bool
    ///
    #[pyfn(m, "push_current_external")]
    fn push_current_external_py(
        id: u64,
        node_id: u64,
        start_time: f64,
        url: &str,
        library: String,
        method: String,
    ) -> PyResult<bool> {
        let parse_url = Url::parse(url).unwrap();
        let host = Some(parse_url.host_str().unwrap_or("undef").to_string());
        let port = parse_url.port();
        let path = parse_url.path();

        Ok(core::TRANSACTION_CACHE.write().unwrap().push_current(
            id,
            StackNode::External(ExternalNode::new(
                node_id,
                start_time,
                host.unwrap_or_else(|| "undef".to_string()).to_string(),
                port.unwrap_or(0),
                library,
                method,
                path,
            )),
        ))
    }

    /// Push database trace node to current transaction
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :param int node_id: ID of TransactionNode. Object.__id__ as usual.
    /// :param float start_time: Timestamp when TransactionNode is activated
    /// :param str database_product: Name of database product
    /// :param str database_name: Name of database name or database file path
    /// :param str host: Host of database instanse
    /// :param int port: Port of database instanse
    /// :param str operation: SQL Operation
    /// :param str target: Target table/view
    /// :param str sql: Obfuscated sql
    ///
    #[pyfn(m, "push_current_database")]
    fn push_current_database_py(
        id: u64,
        node_id: u64,
        start_time: f64,
        database_product: String,
        database_name: String,
        host: Option<String>,
        port: Option<u16>,
        operation: String,
        target: String,
        sql: String,
    ) -> PyResult<bool> {
        let host: String = host.unwrap_or("".to_string());
        let port: u16 = port.unwrap_or(0);
        Ok(core::TRANSACTION_CACHE.write().unwrap().push_current(
            id,
            StackNode::Database(DatabaseNode::new(
                node_id,
                start_time,
                host,
                port,
                database_product,
                database_name,
                operation,
                target,
                sql,
            )),
        ))
    }

    /// Push cache trace node to current transaction
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :param int node_id: ID of TransactionNode. Object.__id__ as usual.
    /// :param float start_time: Timestamp when TransactionNode is activated
    /// :param str database_product: Name of database product
    /// :param str database_name: Name of database name.
    /// :param str host: Host of cache instanse
    /// :param int port: Port of cache instanse
    ///
    #[pyfn(m, "push_current_cache")]
    fn push_current_cache_py(
        id: u64,
        node_id: u64,
        start_time: f64,
        database_name: String,
        host: String,
        port: u16,
        operation: String,
        database_product: String,
    ) -> PyResult<bool> {
        Ok(core::TRANSACTION_CACHE.write().unwrap().push_current(
            id,
            StackNode::Cache(CacheNode::new(
                node_id,
                start_time,
                host,
                port,
                database_product,
                database_name,
                operation,
            )),
        ))
    }

    /// Pop TraceNode from TraceStack. Call when TransactionNode is closed.
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :param int node_id: ID of TransactionNode. Object.__id__ as usual.
    /// :param float end_time: Timestamp when TransactionNode is closed.
    /// :return: Return ID of Parent TransactionNode. If current TransactionNode not found return None
    /// :rtype: int or None
    ///
    #[pyfn(m, "pop_current")]
    fn pop_current_py(id: u64, node_id: u64, end_time: f64) -> PyResult<Option<u64>> {
        Ok(core::TRANSACTION_CACHE
            .write()
            .unwrap()
            .pop_current(id, node_id, end_time))
    }

    /// Drop transaction from transaction cache
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :return: the return code.
    /// :rtype: bool
    ///
    #[pyfn(m, "drop_transaction")]
    fn drop_transaction_py(id: u64) -> PyResult<bool> {
        Ok(core::TRANSACTION_CACHE
            .write()
            .unwrap()
            .drop_transaction(id))
    }

    /// Set transaction path
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :param str path: Path for Transaction. URI or handler name as usual.
    /// :return: the return code.
    /// :rtype: bool
    ///
    #[pyfn(m, "set_transaction_path")]
    fn set_transaction_path_py(id: u64, path: String) -> PyResult<bool> {
        Ok(core::TRANSACTION_CACHE
            .write()
            .unwrap()
            .set_transaction_path(id, path))
    }

    /// Dump transaction into JSON string
    ///
    /// :param int id: Transaction ID. ThreadID as usual.
    /// :return: The JSON string . If Transaction not found return empty string
    /// :rtype: str
    ///
    #[pyfn(m, "dump_transaction")]
    fn dump_transaction_py(id: u64) -> PyResult<String> {
        Ok(core::TRANSACTION_CACHE
            .write()
            .unwrap()
            .dump_transaction(id))
    }

    /// Activate output transport to PAMCollector
    ///
    /// :param str token: Secret token for auth on PAMCollector.
    /// :param str addr: Address with format host:port for connect to PAMCollector instance .
    /// :return: the return code.
    /// :rtype: bool
    ///
    #[pyfn(m, "activate")]
    fn activate_py(token: &str, addr: &str) -> PyResult<bool> {
        let output_transport: PamCollectorOutput =
            PamCollectorOutput::new(token.to_owned(), addr.to_owned());
        thread::spawn(move || {
            output_transport.start();
        });
        Ok(true)
    }
    Ok(())
}
