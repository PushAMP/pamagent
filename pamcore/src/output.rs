use std::io::prelude::*;
use std::net::TcpStream;
use std::collections::VecDeque;

lazy_static! {
    pub static ref OUTPUT_QUEUE:Arc<Mutex<VecDeque<String>>> = {
        let vector: VecDeque<String> = VecDeque::new();
        Arc::new(Mutex::new(vector))
    };
}


fn get_connection(addr: &str) -> Option<TcpStream> {
    let stream = TcpStream::connect(addr);
    println!("CONN");
    match stream {
        Ok(s) => Some(s),
        Err(e) => {println!("Err {:?}", e); None}
    }
}


use std::sync::{Arc, Mutex};
use std::thread;
pub struct PamCollectorOutput {
    addr: String,
}

pub trait Output{
    fn start(&self);
}

impl PamCollectorOutput {
    pub fn new(addr: String) -> PamCollectorOutput {
        PamCollectorOutput {
            addr: addr,
        }
    }
}

impl Output for PamCollectorOutput {
    fn start(&self) {
        let addr: String = self.addr.clone();
        thread::spawn(move || loop {
            let val = OUTPUT_QUEUE.lock().unwrap().remove(0);
            let stream: Option<TcpStream> = get_connection(&addr);
            match stream {
                Some(mut s) => {
                    match val {
                        Some(v) => {
                            let _ = s.write(v.as_bytes());
                        },
                        None => println!("None")
                    };

                },
                None => println!("Not socket")
            }
        });
    }
}
