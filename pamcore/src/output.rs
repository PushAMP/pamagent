use std::collections::VecDeque;
use std::io::prelude::*;
use std::net::TcpStream;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use std::thread;

use std::cell::RefCell;
use std::rc::Rc;
use std::borrow::Cow;

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
        Err(e) => {
            println!("Err {:?}", e);
            None
        }
    }
}

pub struct PamCollectorOutput {
    addr: String,
    token: String,
}

pub trait Output {
    fn start(&self);
}

impl PamCollectorOutput {
    pub fn new(token: String, addr: String) -> PamCollectorOutput {
        PamCollectorOutput { addr, token }
    }
}

impl Output for PamCollectorOutput {
    fn start(&self) {
        let addr: String =  self.addr.clone();
        let token: String = self.token.clone();

        thread::spawn(move || {
//            println!("{}", addr);
            thread_local! {
                pub static addr: RefCell<u32> = RefCell::new(1);

                #[allow(unused)]
                static token: RefCell<f32> = RefCell::new(1.0);
            }
            fn stream_v(shared_stream: Rc<RefCell<TcpStream>>) {
                println!("Output loop started");
                loop {
                    match shared_stream.borrow_mut().try_clone() {
                        Ok(mut s) => {
                            let val = OUTPUT_QUEUE.lock().unwrap().pop_front();
                            match val {
                                Some(v) => {
                                    let _ = s.write(v.as_bytes());
                                    let read_bytes = s.read(&mut [0; 128]);
                                    match read_bytes {
                                        Ok(v) => {
                                            match v {
                                                0 => {println!("Server close connect");
                                                    recreate_stream(shared_stream)
                                                },
                                                _ => {println!("OK")}
                                            };
                                        },
                                        Err(e) => {println!("Error {}", e)}
                                    }
                                }
                                None => {
                                    thread::sleep(Duration::from_millis(40));
                                    ()
                                }
                            }
                        }
                        Err(_) => {recreate_stream(shared_stream);
                            println!("Error create underlayng socket")},
                    }
                }

            }

            fn recreate_stream(shared_stream: Rc<RefCell<TcpStream>>) {
                let stream: Option<TcpStream> = get_connection(&addr);
                let status_w = shared_stream.borrow_mut().write(token.as_bytes()).and_then(|_| {
                    let mut buffer = [0; 10];
                    shared_stream.borrow_mut().read(&mut buffer)
                        .and_then(|r| match r {
                            0 => {
                                println!("Token not valid");
                                Ok(0)
                            }
                            _ => {
                                println!("Token valid");
//                                    stream_v(&s);
                                Ok(r)
                            }
                        })
                        .or(Ok(0))
                });
                match status_w {
                    Ok(v) => stream_v(shared_stream),
                    Err(e) => println!("Error: {}", e)
                }
            }

            let stream: Option<TcpStream> = get_connection(&addr);
            let shared_stream: Rc<RefCell<TcpStream>> = Rc::new(RefCell::new(stream.unwrap()));
            let status_w = shared_stream.borrow_mut().write(token.as_bytes()).and_then(|_| {
                let mut buffer = [0; 10];
                shared_stream.borrow_mut().read(&mut buffer)
                    .and_then(|r| match r {
                        0 => {
                            println!("Token not valid");
                            Ok(0)
                        }
                        _ => {
                            println!("Token valid");
//                                    stream_v(&s);
                            Ok(r)
                        }
                    })
                    .or(Ok(0))
            });
            match status_w {
                Ok(v) => stream_v(shared_stream),
                Err(e) => println!("Error: {}", e)
            }
        });
    }
}
