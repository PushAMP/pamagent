
#![crate_type = "dylib"]
#[macro_use]
extern crate cpython;
extern crate native_tls;
#[macro_use]
extern crate lazy_static;
use cpython::{PyResult, Python};
use std::sync::Mutex;
use std::collections::hash_map::Entry;
use std::collections::HashMap;
use std::cell::RefCell;

#[derive(Debug)]
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
#[derive(Debug)]
struct TransactionNode {
    base_name: String,
    nodes_stack: RefCell<Vec<StackNode>>,
    trace_node_count: RefCell<u8>,
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
    m.add(py,
             "make_transaction_node",
             py_fn!(py, make_transaction_node(base_name: String)))?;
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
    Ok(())
});

fn make_transaction_node(_: Python, base_name: String) -> PyResult<bool> {
    let node = TransactionNode {
        base_name: base_name,
        nodes_stack: RefCell::new(vec![]),
        trace_node_count: RefCell::new(0),
    };
    println!("{:?}", TRANSACTION_CACHE.lock().unwrap().get(&1));
    TRANSACTION_CACHE.lock().unwrap().insert(1, node);
    Ok(true)
}

fn set_transaction(_: Python, id: u64, transaction: String) -> PyResult<bool> {
    let mut tr_cache = TRANSACTION_CACHE.lock().unwrap();
    match tr_cache.entry(id) {
        Entry::Occupied(_) => Ok(false),
        Entry::Vacant(v) => {
            v.insert(TransactionNode {
                         base_name: transaction,
                         nodes_stack: RefCell::new(vec![]),
                         trace_node_count: RefCell::new(0),
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
    println!("{:?}", c_tr.nodes_stack.borrow());
    return Ok(true);
}

fn pop_current(_: Python, id: u64, node_id: u64, end_time: f64) -> PyResult<Option<u64>> {
    let tr_cache = TRANSACTION_CACHE.lock().unwrap();
    let c_tr = match tr_cache.get(&id) {
        Some(v) => v,
        None => return Ok(None),
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

    println!("POP {:?}", cur_id);
    println!("TR {:?}", c_tr);
    if cur_id.node_id == node_id {
        let ln = c_tr.nodes_stack.borrow().len();
        let ref mut parent_node = c_tr.nodes_stack.borrow_mut()[ln - 1];
        parent_node.process_child(cur_id);
        let t = parent_node.node_id;
        return Ok(Some(t));
    };


    return Ok(None);
}


fn drop_transaction(_: Python, id: u64) -> PyResult<bool> {
    let mut tr_cache = TRANSACTION_CACHE.lock().unwrap();
    match tr_cache.remove(&id) {
        Some(_) => Ok(true),
        None => Ok(false),
    }
}

