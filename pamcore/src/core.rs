use std::sync::RwLock;
use std::collections::hash_map::Entry;
use std::collections::HashMap;
use rand;
use serde_json;

lazy_static! {
    static ref TRANSACTION_CACHE: RwLock<HashMap<u64, TransactionNode>> = {
        let m = RwLock::new(HashMap::new());
        m
    };
}


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
    nodes_stack: Vec<StackNode>,
    trace_node_count: u8,
    guid: String,
    path: String,
}

impl TransactionNode {
    fn set_path(&mut self, path: String) {
        self.path = path;
    }
}


pub fn set_transaction(id: u64, transaction: String, path: Option<String>) -> bool {
    let mut tr_cache = TRANSACTION_CACHE.write().unwrap();
    match tr_cache.entry(id) {
        Entry::Occupied(_) => false,
        Entry::Vacant(v) => {
            v.insert(TransactionNode {
                         base_name: transaction,
                         nodes_stack: vec![],
                         trace_node_count: 0,
                         guid: format!("{:x}", rand::random::<u64>()),
                         path: path.unwrap_or(format!("")),
                     });
            true
        }
    }
}

pub fn get_transaction(id: u64) -> Option<u64> {
    let tr_cache = TRANSACTION_CACHE.read().unwrap();
    match tr_cache.get(&id) {
        Some(_) => Some(id),
        None => None,
    }
}

pub fn drop_transaction(id: u64) -> bool {
    let mut tr_cache = TRANSACTION_CACHE.write().unwrap();
    match tr_cache.remove(&id) {
        Some(val) => {
            let j = serde_json::to_string(&val).unwrap_or("".to_uppercase());
            println!("{}", j);
            true
        }
        None => false,
    }
}

pub fn push_current(id: u64, node_id: u64, start_time: f64) -> bool {
    let mut tr_cache = TRANSACTION_CACHE.write().unwrap();
    let c_tr = match tr_cache.get_mut(&id) {
        Some(v) => v,
        None => return false,
    };
    c_tr.nodes_stack.push(StackNode {
                              node_id: node_id,
                              childrens: vec![],
                              start_time: start_time,
                              end_time: 0.0,
                              exclusive: 0.0,
                              node_count: 0,
                              duration: 0.0,
                          });
    return true;
}

pub fn pop_current(id: u64, node_id: u64, end_time: f64) -> Option<u64> {
    let mut tr_cache = TRANSACTION_CACHE.write().unwrap();
    let c_tr = match tr_cache.get_mut(&id) {
        Some(v) => v,
        None => return None,
    };
    let ln = c_tr.nodes_stack.len();
    if ln == 1 {
        let ref mut root_id = c_tr.nodes_stack[0];
        root_id.set_endtime(end_time);
        root_id.comp_exclusive();
        c_tr.trace_node_count += 1;
        return None;
    };
    let cur_id = match c_tr.nodes_stack.pop() {
        Some(mut v) => {
            v.set_endtime(end_time);
            v.comp_exclusive();
            c_tr.trace_node_count += 1;
            v
        }
        None => return None,
    };
    let ln = c_tr.nodes_stack.len();
    println!("LLLLL {:?}", ln);

    if cur_id.node_id == node_id {
        let ref mut parent_node = c_tr.nodes_stack[ln - 1];
        parent_node.process_child(cur_id);
        let t = parent_node.node_id;
        println!("PARENT {}", t);
        return Some(t);
    };


    return None;
}

pub fn get_transaction_start_time(id: u64) -> f64 {
    let tr_cache = TRANSACTION_CACHE.read().unwrap();
    let tr = match tr_cache.get(&id) {
        Some(tr) => tr,
        None => return 0.0,
    };
    let st: f64;
    if tr.nodes_stack.len() > 0 {
        st = tr.nodes_stack[0].start_time;
    } else {
        st = 0.0
    };
    st
}

pub fn get_transaction_end_time(id: u64) -> f64 {
    let tr_cache = TRANSACTION_CACHE.read().unwrap();
    let tr = match tr_cache.get(&id) {
        Some(tr) => tr,
        None => return 0.0,
    };
    let st: f64;
    if tr.nodes_stack.len() > 0 {
        st = tr.nodes_stack[0].end_time;
    } else {
        st = 0.0
    };
    st
}

pub fn set_transaction_path(id: u64, path: String) -> bool {
    let mut tr_cache = TRANSACTION_CACHE.write().unwrap();
    match tr_cache.get_mut(&id) {
        Some(tr) => tr.set_path(path),
        None => return false,
    };
    true
}

