
#![crate_type = "dylib"]
#[macro_use]
extern crate cpython;
extern crate serde;
extern crate serde_json;
#[macro_use]
extern crate serde_derive;
#[macro_use]
extern crate lazy_static;
extern crate rand;

use cpython::{PyResult, Python};

mod core;
use core::TransactionCache;
py_module_initializer!(pamagent_core,
                       initpamagent_core,
                       PyInit_pamagent_core,
                       |py, m| {
    m.add(py, "__doc__", "This module is implemented in Rust.")?;
    m.add(py,
          "set_transaction",
          py_fn!(py,
                 set_transaction_py(id: u64, transaction: String, path: Option<String>)))?;
    m.add(py,
          "get_transaction",
          py_fn!(py, get_transaction_py(id: u64)))?;
    m.add(py,
          "drop_transaction",
          py_fn!(py, drop_transaction_py(id: u64)))?;
    m.add(py,
          "push_current",
          py_fn!(py, push_current_py(id: u64, node_id: u64, start_time: f64)))?;
    m.add(py,
          "pop_current",
          py_fn!(py, pop_current_py(id: u64, node_id: u64, end_time: f64)))?;
    m.add(py,
          "get_transaction_start_time",
          py_fn!(py, get_transaction_start_time_py(id: u64)))?;
    m.add(py,
          "get_transaction_end_time",
          py_fn!(py, get_transaction_end_time_py(id: u64)))?;
    m.add(py,
          "set_transaction_path",
          py_fn!(py, set_transaction_path_py(id: u64, path: String)))?;

    Ok(())
});

fn set_transaction_py(_: Python,
                      id: u64,
                      transaction: String,
                      path: Option<String>)
                      -> PyResult<bool> {
    Ok(core::TRANSACTION_CACHE
           .write()
           .unwrap()
           .set_transaction(id, transaction, path))
}


fn get_transaction_py(_: Python, id: u64) -> PyResult<Option<u64>> {
    Ok(core::TRANSACTION_CACHE
           .read()
           .unwrap()
           .availability_transaction(id))
}

fn get_transaction_start_time_py(_: Python, id: u64) -> PyResult<f64> {
    Ok(core::TRANSACTION_CACHE
           .read()
           .unwrap()
           .get_transaction_start_time(id))
}

fn get_transaction_end_time_py(_: Python, id: u64) -> PyResult<f64> {
    Ok(core::TRANSACTION_CACHE
           .read()
           .unwrap()
           .get_transaction_end_time(id))
}

fn push_current_py(_: Python, id: u64, node_id: u64, start_time: f64) -> PyResult<bool> {
    Ok(core::TRANSACTION_CACHE
           .write()
           .unwrap()
           .push_current(id, node_id, start_time))
}

fn pop_current_py(_: Python, id: u64, node_id: u64, end_time: f64) -> PyResult<Option<u64>> {
    Ok(core::TRANSACTION_CACHE
           .write()
           .unwrap()
           .pop_current(id, node_id, end_time))
}

fn drop_transaction_py(_: Python, id: u64) -> PyResult<bool> {
    Ok(core::TRANSACTION_CACHE
           .write()
           .unwrap()
           .drop_transaction(id))
}

fn set_transaction_path_py(_: Python, id: u64, path: String) -> PyResult<bool> {
    Ok(core::TRANSACTION_CACHE
           .write()
           .unwrap()
           .set_transaction_path(id, path))
}

