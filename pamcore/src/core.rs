use std::sync::RwLock;
use std::collections::hash_map::Entry;
use std::collections::HashMap;
use rand;
use serde_json;

const DEFAULT_TIME_VAL: f64 = 0.0;

lazy_static! {
    pub static  ref TRANSACTION_CACHE: RwLock<TrMap> = {
        let m = RwLock::new(TrMap::new());
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

pub struct TrMap(HashMap<u64, TransactionNode>);

pub trait TransactionCache {
    fn new() -> TrMap;
    fn get_transaction_start_time(&self, id: u64) -> f64;
    fn get_transaction_end_time(&self, id: u64) -> f64;
    fn set_transaction(&mut self, id: u64, transaction: String, path: Option<String>) -> bool;
    fn availability_transaction(&self, id: u64) -> Option<u64>;
    fn drop_transaction(&mut self, id: u64) -> bool;
    fn push_current(&mut self, id: u64, node_id: u64, start_time: f64) -> bool;
    fn pop_current(&mut self, id: u64, node_id: u64, end_time: f64) -> Option<u64>;
    fn set_transaction_path(&mut self, id: u64, path: String) -> bool;
}

impl TransactionCache for TrMap {
    fn new() -> TrMap {
        TrMap(HashMap::new())
    }
    fn set_transaction(&mut self, id: u64, transaction: String, path: Option<String>) -> bool {
        match self.0.entry(id) {
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
    fn get_transaction_start_time(&self, id: u64) -> f64 {
        match self.0.get(&id) {
            Some(tr) => {
                if tr.nodes_stack.len() > 0 {
                    tr.nodes_stack[0].start_time;
                }
                DEFAULT_TIME_VAL
            }
            None => DEFAULT_TIME_VAL,
        }
    }
    fn get_transaction_end_time(&self, id: u64) -> f64 {
        match self.0.get(&id) {
            Some(tr) => {
                if tr.nodes_stack.len() > 0 {
                    tr.nodes_stack[0].end_time;
                }
                DEFAULT_TIME_VAL
            }
            None => DEFAULT_TIME_VAL,
        }
    }
    fn availability_transaction(&self, id: u64) -> Option<u64> {
        match self.0.get(&id) {
            Some(_) => Some(id),
            None => None,
        }
    }
    fn drop_transaction(&mut self, id: u64) -> bool {
        match self.0.remove(&id) {
            Some(val) => {
                let j = serde_json::to_string(&val).unwrap_or("".to_uppercase());
                println!("{}", j);
                true
            }
            None => false,
        }
    }
    fn push_current(&mut self, id: u64, node_id: u64, start_time: f64) -> bool {
        match self.0.get_mut(&id) {
            Some(v) => {
                v.nodes_stack.push(StackNode {
                                       node_id: node_id,
                                       childrens: vec![],
                                       start_time: start_time,
                                       end_time: 0.0,
                                       exclusive: 0.0,
                                       node_count: 0,
                                       duration: 0.0,
                                   });
                true
            }
            None => false,
        }
    }
    fn pop_current(&mut self, id: u64, node_id: u64, end_time: f64) -> Option<u64> {
        let c_tr = match self.0.get_mut(&id) {
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
    fn set_transaction_path(&mut self, id: u64, path: String) -> bool {
        match self.0.get_mut(&id) {
            Some(tr) => {
                tr.set_path(path);
                true
            }
            None => false,
        }
    }
}

