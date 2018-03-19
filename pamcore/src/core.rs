use std::sync::RwLock;
use std::collections::hash_map::Entry;
use std::collections::HashMap;
use rand;
use serde_json;
use output;
const DEFAULT_TIME_VAL: f64 = 0.0;

lazy_static! {
    pub static  ref TRANSACTION_CACHE: RwLock<TrMap> = {
        RwLock::new(TrMap::new())
    };
}
#[derive(Debug, Serialize)]
#[serde(tag = "type")]
pub enum StackNode {
    Func(FuncNode),
    External(ExternalNode),
    Database(DatabaseNode),
    Cache(CacheNode),
}

impl StackNode {
    fn get_start_time(&self) -> f64 {
        match *self {
            StackNode::Func(ref x) => x.start_time,
            StackNode::External(ref x) => x.start_time,
            StackNode::Database(ref x) => x.start_time,
            StackNode::Cache(ref x) => x.start_time,
        }
    }
    fn get_end_time(&self) -> f64 {
        match *self {
            StackNode::Func(ref x) => x.end_time,
            StackNode::External(ref x) => x.end_time,
            StackNode::Database(ref x) => x.end_time,
            StackNode::Cache(ref x) => x.end_time,
        }
    }
    fn set_endtime(&mut self, end_time: f64) {
        match *self {
            StackNode::Func(ref mut x) => x.set_endtime(end_time),
            StackNode::External(ref mut x) => x.set_endtime(end_time),
            StackNode::Database(ref mut x) => x.set_endtime(end_time),
            StackNode::Cache(ref mut x) => x.set_endtime(end_time),
        }
    }
    fn comp_exclusive(&mut self) -> f64 {
        match *self {
            StackNode::Func(ref mut x) => x.comp_exclusive(),
            StackNode::External(ref mut x) => x.comp_exclusive(),
            StackNode::Database(ref mut x) => x.comp_exclusive(),
            StackNode::Cache(ref mut x) => x.comp_exclusive(),
        }
    }
    fn get_node_id(&self) -> u64 {
        match *self {
            StackNode::Func(ref x) => x.node_id,
            StackNode::External(ref x) => x.node_id,
            StackNode::Database(ref x) => x.node_id,
            StackNode::Cache(ref x) => x.node_id,
        }
    }
    fn get_duration(&self) -> f64 {
        match *self {
            StackNode::Func(ref x) => x.duration,
            StackNode::External(ref x) => x.duration,
            StackNode::Database(ref x) => x.duration,
            StackNode::Cache(ref x) => x.duration,
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
            StackNode::Database(ref mut x) => {
                x.exclusive -= node.get_duration();
                x.childrens.push(node);
            }
            StackNode::Cache(ref mut x) => {
                x.exclusive -= node.get_duration();
                x.childrens.push(node);
            }
        }
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
    method: String,
    path: String,
}

impl ExternalNode {
    pub fn new(
        node_id: u64,
        start_time: f64,
        host: String,
        port: u16,
        library: String,
        method: String,
        path: &str,
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
            method: method,
            path: path.to_string(),
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
pub struct DatabaseNode {
    node_id: u64,
    childrens: Vec<StackNode>,
    start_time: f64,
    end_time: f64,
    exclusive: f64,
    node_count: u8,
    duration: f64,
    host: String,
    port: u16,
    database_product: String,
    database_name: String,
    operation: String,
    target: String,
    sql: String,
}

impl DatabaseNode {
    pub fn new(
        node_id: u64,
        start_time: f64,
        host: String,
        port: u16,
        database_product: String,
        database_name: String,
        operation: String,
        target: String,
        sql: String,
    ) -> DatabaseNode {
        let mut default_host: &str = "";
        let mut default_port: u16 = 0;
        if database_product == "PostgreSQL" {
            default_host = "127.0.0.1";
            default_port = 5432;
        } else if database_product == "MySQL" {
            default_host = "127.0.0.1";
            default_port = 3306;
        };
        let target_host = match host.as_ref() {
            "" => default_host.to_string(),
            _ => host,
        };
        let target_port = match port {
            0 => default_port,
            _ => port,
        };
        DatabaseNode {
            node_id: node_id,
            childrens: vec![],
            start_time: start_time,
            end_time: DEFAULT_TIME_VAL,
            exclusive: DEFAULT_TIME_VAL,
            node_count: 0,
            duration: DEFAULT_TIME_VAL,
            host: target_host.to_string(),
            port: target_port,
            database_name: database_name.to_string(),
            database_product: database_product.to_string(),
            operation: operation.to_string(),
            target: target.to_string(),
            sql: sql,
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
pub struct CacheNode {
    node_id: u64,
    childrens: Vec<StackNode>,
    start_time: f64,
    end_time: f64,
    exclusive: f64,
    node_count: u8,
    duration: f64,
    host: String,
    port: u16,
    database_product: String,
    database_name: String,
    operation: String,
}

impl CacheNode {
    pub fn new(
        node_id: u64,
        start_time: f64,
        host: String,
        port: u16,
        database_product: String,
        database_name: String,
        operation: String,
    ) -> CacheNode {
        CacheNode {
            node_id: node_id,
            childrens: vec![],
            start_time: start_time,
            end_time: DEFAULT_TIME_VAL,
            exclusive: DEFAULT_TIME_VAL,
            node_count: 0,
            duration: DEFAULT_TIME_VAL,
            host: host,
            port: port,
            database_name: database_name.to_string(),
            database_product: database_product.to_string(),
            operation: operation.to_string(),
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

impl TransactionNode {
    fn set_path(&mut self, path: String) {
        self.path = path;
    }
    fn dump(&self) -> String {
        let dump_str: String = serde_json::to_string(self).unwrap();
        dump_str
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
    fn dump_transaction(&self, id: u64) -> String;
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
                    path: path.unwrap_or_else(|| "".to_owned()),
                });
                true
            }
        }
    }
    fn get_transaction_start_time(&self, id: u64) -> f64 {
        match self.0.get(&id) {
            Some(tr) => {
                if !tr.nodes_stack.is_empty() {
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
                if !tr.nodes_stack.is_empty() {
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
                let j: String = serde_json::to_string(&val).unwrap_or_else(|_| "".to_uppercase());
                output::OUTPUT_QUEUE.lock().unwrap().push_back(j);
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
            let root_id = &mut c_tr.nodes_stack[0];
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

        if cur_id.get_node_id() == node_id {
            let parent_node: &mut StackNode = &mut c_tr.nodes_stack[ln - 1];
            parent_node.process_child(cur_id);
            let t: u64 = parent_node.get_node_id();
            return Some(t);
        };

        None
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
    fn dump_transaction(&self, id: u64) -> String {
        match self.0.get(&id) {
            Some(tr) => tr.dump(),
            None => "".to_owned(),
        }
    }
}
