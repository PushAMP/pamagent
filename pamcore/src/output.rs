use std::collections::VecDeque;
use std::io::prelude::*;
use std::io::Error;
use std::net::TcpStream;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use std::thread;

use std::cell::RefCell;
use std::rc::Rc;

lazy_static! {
    pub static ref OUTPUT_QUEUE:Arc<Mutex<VecDeque<String>>> = {
        let vector: VecDeque<String> = VecDeque::new();
        Arc::new(Mutex::new(vector))
    };
}

fn get_connection(addr: &str) -> Option<TcpStream> {
    let stream: Result<TcpStream, Error> = TcpStream::connect(addr);
    match stream {
        Ok(s) => Some(s),
        Err(e) => {
            //            println!("Error connect {:?}", e);
            None
        }
    }
}
#[derive(Clone)]
pub struct PamCollectorOutput {
    addr: String,
    token: String,
}

pub trait Output {
    fn start(&self);
    fn recreate_stream(&self) -> TcpStream;
    fn consume_events(&self, shared_stream: Rc<RefCell<TcpStream>>);
}

impl PamCollectorOutput {
    pub fn new(token: String, addr: String) -> PamCollectorOutput {
        PamCollectorOutput { addr, token }
    }
}

impl Output for PamCollectorOutput {
    fn start(&self) {
        let shared_stream: Rc<RefCell<TcpStream>> = Rc::new(RefCell::new(self.recreate_stream()));
        self.consume_events(shared_stream);
    }

    fn recreate_stream(&self) -> TcpStream {
        let mut tmp_stream: Option<TcpStream> = None;
        let mut reconnect_status: bool = false;
        while !reconnect_status {
            let stream_opt: Option<TcpStream> = get_connection(&self.addr);
            let mut stream: TcpStream = match stream_opt {
                Some(stream) => stream,
                None => continue,
            };
            let status_w: Result<usize, Error> = stream.write(self.token.as_bytes());
            let status: usize = match status_w {
                Ok(_v) => {
                    let mut buffer: [u8; 10] = [0; 10];
                    match stream.read(&mut buffer) {
                        Ok(v) => match v {
                            0 => {
                                println!("Token invalid. Connection Close");
                                0
                            }
                            _ => {
                                println!("Token Valid");
                                1
                            }
                        },
                        Err(e) => {
                            println!("Error while read handshake byte {}", e);
                            0
                        }
                    }
                }
                Err(e) => {
                    println!("Error while write handshakebytes {}", e);
                    0
                }
            };
            match status {
                0 => continue,
                _ => {
                    tmp_stream = Some(stream);
                    reconnect_status = true;
                }
            };
        }
        tmp_stream.unwrap()
    }

    fn consume_events(&self, shared_stream: Rc<RefCell<TcpStream>>) {
        println!("Output loop started");
        let mut need_recreate: bool = false;
        loop {
            if need_recreate {
                thread::sleep(Duration::from_secs(10));
                let new_stream: TcpStream = self.recreate_stream();
                shared_stream.replace(new_stream);
                need_recreate = false;
            }

            match shared_stream.borrow_mut().try_clone() {
                Ok(mut s) => {
                    let val: Option<String> = OUTPUT_QUEUE.lock().unwrap().pop_front();
                    match val {
                        Some(v) => {
                            let _ = s.write(v.as_bytes());
                            let read_bytes: Result<usize, Error> = s.read(&mut [0; 128]);
                            match read_bytes {
                                Ok(v) => {
                                    match v {
                                        0 => {
                                            println!("Server close connect");
                                            need_recreate = true;
                                        }
                                        _ => println!("OK"),
                                    };
                                }
                                Err(e) => {
                                    println!("Error while read payload response {}", e);
                                    need_recreate = true;
                                }
                            }
                        }
                        None => {
                            thread::sleep(Duration::from_millis(400));
                            ()
                        }
                    }
                }
                Err(_) => {
                    println!("Error create underlayng socket");
                    need_recreate = true;
                }
            };
        }
    }
}
