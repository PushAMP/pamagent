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
#[serde(tag = "type")]
pub enum StackNode {
    Func(FuncNode),
    External(ExternalNode),
}

impl StackNode {
    fn get_start_time(&self) -> f64 {
        match *self {
            StackNode::Func(ref x) => x.start_time,
            StackNode::External(ref x) => x.start_time,
        }
    }
    fn get_end_time(&self) -> f64 {
        match *self {
            StackNode::Func(ref x) => x.end_time,
            StackNode::External(ref x) => x.end_time,
        }
    }
    fn set_endtime(&mut self, end_time: f64) {
        match *self {
            StackNode::Func(ref mut x) => x.set_endtime(end_time),
            StackNode::External(ref mut x) => x.set_endtime(end_time),
        }
    }
    fn comp_exclusive(&mut self) -> f64 {
        match *self {
            StackNode::Func(ref mut x) => x.comp_exclusive(),
            StackNode::External(ref mut x) => x.comp_exclusive(),
        }
    }

    fn get_exclusive(&self) -> f64 {
        match *self {
            StackNode::Func(ref x) => x.exclusive,
            StackNode::External(ref x) => x.exclusive,
        }
    }

    fn get_node_id(&self) -> u64 {
        match *self {
            StackNode::Func(ref x) => x.node_id,
            StackNode::External(ref x) => x.node_id,
        }
    }
    fn get_duration(&self) -> f64 {
        match *self {
            StackNode::Func(ref x) => x.duration,
            StackNode::External(ref x) => x.duration,
        }
    }
    fn process_child(&mut self, node: StackNode) {
        match *self {
            StackNode::Func(ref mut x) => {
                x.exclusive -= node.get_duration();
                x.childrens.push(node);
            }
            StackNode::External(ref mut x) => {
                x.exclusive -= node.get_duration();
                x.childrens.push(node);
            }
        }
    }
    fn node_type(&self) -> &str {
        match *self {
            StackNode::Func(_) => "func",
            StackNode::External(_) => "external",
        }
    }
    fn get_library(&self) -> Option<String> {
        match *self {
            StackNode::Func(_) => None,
            StackNode::External(ref v) => Some(v.library.to_owned()),
        }
    }
    fn get_host(&self) -> Option<String> {
        match *self {
            StackNode::Func(_) => None,
            StackNode::External(ref v) => Some(v.host.to_owned()),
        }
    }
    fn get_port(&self) -> Option<u16> {
        match *self {
            StackNode::Func(_) => None,
            StackNode::External(ref v) => Some(v.port),
        }
    }

    fn get_func_name(&self) -> Option<String> {
        match *self {
            StackNode::Func(ref v) => Some(v.func_name.to_owned()),
            StackNode::External(_) => None,
        }
    }

    fn get_parent(&self) -> Vec<PlainNode> {
        let mut pla = Vec::new();

        match *self {
            StackNode::Func(ref x) => {
                for u in &x.childrens {
                    let pl_node: PlainNode = PlainNode {
                        node_id: u.get_node_id(),
                        parent_id: x.node_id,
                        node_type: u.node_type(),
                        start_time: u.get_start_time(),
                        end_time: u.get_end_time(),
                        exclusive: u.get_exclusive(),
                        duration: u.get_duration(),
                        library: u.get_library(),
                        host: None,
                        port: None,
                        func_name: u.get_func_name(),
                    };
                    pla.push(pl_node);
                    let sub = u.get_parent();
                    pla.extend(sub);
                }
            }
            StackNode::External(ref x) => {
                for u in &x.childrens {
                    let pl_node: PlainNode = PlainNode {
                        node_id: u.get_node_id(),
                        parent_id: x.node_id,
                        node_type: u.node_type(),
                        start_time: u.get_start_time(),
                        end_time: u.get_end_time(),
                        exclusive: u.get_exclusive(),
                        duration: u.get_duration(),
                        library: u.get_library(),
                        host: u.get_host(),
                        port: u.get_port(),
                        func_name: u.get_func_name(),
                    };
                    pla.push(pl_node);
                    let sub = u.get_parent();
                    pla.extend(sub);
                }
            }
        }

        pla
    }
}

#[derive(Debug, Serialize)]
pub struct FuncNode {
    node_id: u64,
    childrens: Vec<StackNode>,
    start_time: f64,
    end_time: f64,
    exclusive: f64,
    node_count: u8,
    duration: f64,
    func_name: String,
}
#[derive(Debug, Serialize)]
struct PlainNode<'a> {
    node_type: &'a str,
    node_id: u64,
    parent_id: u64,
    start_time: f64,
    end_time: f64,
    exclusive: f64,
    duration: f64,
    library: Option<String>,
    host: Option<String>,
    port: Option<u16>,
    func_name: Option<String>,
}

impl FuncNode {
    pub fn new(node_id: u64, start_time: f64, func_name: String) -> FuncNode {
        FuncNode {
            node_id: node_id,
            childrens: vec![],
            start_time: start_time,
            end_time: DEFAULT_TIME_VAL,
            exclusive: DEFAULT_TIME_VAL,
            node_count: 0,
            duration: DEFAULT_TIME_VAL,
            func_name: func_name,
        }
    }
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
}

#[derive(Debug, Serialize)]
pub struct ExternalNode {
    node_id: u64,
    childrens: Vec<StackNode>,
    start_time: f64,
    end_time: f64,
    exclusive: f64,
    node_count: u8,
    duration: f64,
    host: String,
    port: u16,
    library: String,
}

impl ExternalNode {
    pub fn new(
        node_id: u64,
        start_time: f64,
        host: String,
        port: u16,
        library: String,
    ) -> ExternalNode {
        ExternalNode {
            node_id: node_id,
            childrens: vec![],
            start_time: start_time,
            end_time: DEFAULT_TIME_VAL,
            exclusive: DEFAULT_TIME_VAL,
            node_count: 0,
            duration: DEFAULT_TIME_VAL,
            host: host.to_string(),
            port: port,
            library: library,
        }
    }
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
}

#[derive(Debug, Serialize)]
struct TransactionNode {
    base_name: String,
    nodes_stack: Vec<StackNode>,
    trace_node_count: u8,
    guid: String,
    path: String,
}

#[derive(Debug, Serialize)]
struct PlainTransaction<'a> {
    base_name: &'a str,
    nodes_stack: Vec<PlainNode<'a>>,
    guid: &'a str,
    path: &'a str,
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
    fn push_current(&mut self, id: u64, node: StackNode) -> bool;
    fn pop_current(&mut self, id: u64, node_id: u64, end_time: f64) -> Option<u64>;
    fn set_transaction_path(&mut self, id: u64, path: String) -> bool;
}

impl<'b> TransactionCache for TrMap {
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
                    tr.nodes_stack[0].get_start_time();
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
                    tr.nodes_stack[0].get_end_time();
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
                let f = PlainTransaction {
                    base_name: &val.base_name,
                    nodes_stack: val.nodes_stack[0].get_parent(),
                    guid: &val.guid,
                    path: &val.path,
                };
                println!("{}", j);
                println!("{:?}", f);
                let sr = serde_json::to_string(&f).unwrap_or("".to_uppercase());
                println!("{}", sr);
                true
            }
            None => false,
        }
    }
    fn push_current(&mut self, id: u64, node: StackNode) -> bool {
        match self.0.get_mut(&id) {
            Some(v) => {
                v.nodes_stack.push(node);
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
            match root_id {
                _ => {
                    root_id.set_endtime(end_time);
                    root_id.comp_exclusive();
                    c_tr.trace_node_count += 1;
                }
            }

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

        if cur_id.get_node_id() == node_id {
            let ref mut parent_node = c_tr.nodes_stack[ln - 1];
            parent_node.process_child(cur_id);
            let t = parent_node.get_node_id();
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
