
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
use std::sync::Mutex;
use std::collections::hash_map::Entry;
use std::collections::HashMap;
use std::cell::RefCell;

#[derive(Debug, Serialize)]
struct StackNode {
    node_id: u64,
    childrens: Vec<StackNode>,
    start_time: f64,
    end_time: f64,
    exclusive: f64,
    node_count: u8,
    duration: f64,
}
impl StackNode {
    fn set_endtime(&mut self, end_time: f64) {
        self.end_time = end_time;
    }
    fn set_duration(&mut self) -> f64 {
        if self.end_time < self.start_time {
            self.end_time = self.start_time
        }
        self.duration = self.end_time - self.start_time;
        self.duration
    }


    fn comp_exclusive(&mut self) -> f64 {
        self.exclusive += self.set_duration();
        if self.exclusive < 0.0 {
            self.exclusive = 0.0;
        }
        self.exclusive

    }

    fn process_child(&mut self, node: StackNode) {
        self.exclusive -= node.duration;
        self.childrens.push(node);
    }
}
#[derive(Debug, Serialize)]
struct TransactionNode {
    base_name: String,
    nodes_stack: RefCell<Vec<StackNode>>,
    trace_node_count: RefCell<u8>,
    guid: String,
}

lazy_static! {
    static ref TRANSACTION_CACHE: Mutex<HashMap<u64, TransactionNode>> = {
        let m = Mutex::new(HashMap::new());
        m
    };
}

py_module_initializer!(pamagent_core,
                       initpamagent_core,
                       PyInit_pamagent_core,
                       |py, m| {
    m.add(py, "__doc__", "This module is implemented in Rust.")?;
    m.add(py,
          "set_transaction",
          py_fn!(py, set_transaction(id: u64, transaction: String)))?;
    m.add(py, "get_transaction", py_fn!(py, get_transaction(id: u64)))?;
    m.add(py,
          "drop_transaction",
          py_fn!(py, drop_transaction(id: u64)))?;
    m.add(py,
          "push_current",
          py_fn!(py, push_current(id: u64, node_id: u64, start_time: f64)))?;
    m.add(py,
          "pop_current",
          py_fn!(py, pop_current(id: u64, node_id: u64, end_time: f64)))?;
    m.add(py,
          "get_transaction_start_time",
          py_fn!(py, get_transaction_start_time(id: u64)))?;
    m.add(py,
          "get_transaction_end_time",
          py_fn!(py, get_transaction_end_time(id: u64)))?;
    Ok(())
});

fn set_transaction(_: Python, id: u64, transaction: String) -> PyResult<bool> {
    let mut tr_cache = match TRANSACTION_CACHE.lock() {
        Ok(v) => v,
        Err(e) => {
            println!("ERROR {:?}", e);
            panic!("DD");
        }
    };
    match tr_cache.entry(id) {
        Entry::Occupied(_) => Ok(false),
        Entry::Vacant(v) => {
            v.insert(TransactionNode {
                         base_name: transaction,
                         nodes_stack: RefCell::new(vec![]),
                         trace_node_count: RefCell::new(0),
                         guid: format!("{:x}", rand::random::<u64>()),
                     });
            Ok(true)
        }
    }
}

fn get_transaction(_: Python, id: u64) -> PyResult<Option<u64>> {
    let tr_cache = TRANSACTION_CACHE.lock().unwrap();
    match tr_cache.get(&id) {
        Some(_) => Ok(Some(id)),
        None => Ok(None),
    }
}

fn get_transaction_start_time(_: Python, id: u64) -> PyResult<f64> {
    let tr_cache = TRANSACTION_CACHE.lock().unwrap();
    let tr = match tr_cache.get(&id) {
        Some(tr) => tr,
        None => return Ok(0.0),
    };
    let st: f64;
    if tr.nodes_stack.borrow().len() > 0 {
        st = tr.nodes_stack.borrow()[0].start_time;
    } else {
        st = 0.0
    };
    Ok(st)
}

fn get_transaction_end_time(_: Python, id: u64) -> PyResult<f64> {
    let tr_cache = TRANSACTION_CACHE.lock().unwrap();
    let tr = match tr_cache.get(&id) {
        Some(tr) => tr,
        None => return Ok(0.0),
    };
    let st: f64;
    if tr.nodes_stack.borrow().len() > 0 {
        st = tr.nodes_stack.borrow()[0].end_time;
    } else {
        st = 0.0
    };
    Ok(st)
}

fn push_current(_: Python, id: u64, node_id: u64, start_time: f64) -> PyResult<bool> {
    let tr_cache = TRANSACTION_CACHE.lock().unwrap();
    let c_tr = match tr_cache.get(&id) {
        Some(v) => v,
        None => return Ok(false),
    };
    c_tr.nodes_stack.borrow_mut().push(StackNode {
                                           node_id: node_id,
                                           childrens: vec![],
                                           start_time: start_time,
                                           end_time: 0.0,
                                           exclusive: 0.0,
                                           node_count: 0,
                                           duration: 0.0,
                                       });
    return Ok(true);
}

fn pop_current(_: Python, id: u64, node_id: u64, end_time: f64) -> PyResult<Option<u64>> {
    let tr_cache = TRANSACTION_CACHE.lock().unwrap();
    let c_tr = match tr_cache.get(&id) {
        Some(v) => v,
        None => return Ok(None),
    };
    let ln = c_tr.nodes_stack.borrow().len();
    if ln == 1 {
        let ref mut root_id = c_tr.nodes_stack.borrow_mut()[0];
        root_id.set_endtime(end_time);
        root_id.comp_exclusive();
        *c_tr.trace_node_count.borrow_mut() += 1;
        return Ok(None);
    };
    let cur_id = match c_tr.nodes_stack.borrow_mut().pop() {
        Some(mut v) => {
            v.set_endtime(end_time);
            v.comp_exclusive();
            *c_tr.trace_node_count.borrow_mut() += 1;
            v
        }
        None => return Ok(None),
    };
    let ln = c_tr.nodes_stack.borrow().len();
    println!("LLLLL {:?}", ln);

    if cur_id.node_id == node_id {
        let ref mut parent_node = c_tr.nodes_stack.borrow_mut()[ln - 1];
        parent_node.process_child(cur_id);
        let t = parent_node.node_id;
        println!("PARENT {}", t);
        return Ok(Some(t));
    };


    return Ok(None);
}

fn drop_transaction(_: Python, id: u64) -> PyResult<bool> {
    let mut tr_cache = TRANSACTION_CACHE.lock().unwrap();
    match tr_cache.remove(&id) {
        Some(val) => {
            let j = serde_json::to_string(&val).unwrap_or("".to_uppercase());
            println!("{}", j);
            Ok(true)
        }
        None => Ok(false),
    }
}

