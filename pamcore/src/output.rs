use std::collections::VecDeque;
use std::io::prelude::*;
use std::net::TcpStream;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use std::thread;

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
        let addr: String = self.addr.clone();
        let token: String = self.token.clone();
        thread::spawn(move || {
            fn stream_v(stream: &TcpStream) {
                println!("Output loop started");
                loop {
                    match stream.try_clone() {
                        Ok(mut s) => {
                            let val = OUTPUT_QUEUE.lock().unwrap().pop_front();
                            match val {
                                Some(v) => {
                                    let _ = s.write(v.as_bytes());
                                }
                                None => {
                                    thread::sleep(Duration::from_millis(40));
                                    ()
                                }
                            }
                        }
                        Err(_) => println!("Error create underlayng socket"),
                    }
                }

            }
            let stream: Option<TcpStream> = get_connection(&addr);

            match stream {
                Some(mut s) => {
                    let _ = s.write(token.as_bytes()).and_then(|_| {
                        let mut buffer = [0; 10];
                        s.read(&mut buffer)
                            .and_then(|r| match r {
                                0 => {
                                    println!("Token not valid");
                                    Ok(0)
                                }
                                _ => {
                                    println!("Token valid");
                                    stream_v(&s);
                                    Ok(r)
                                }
                            })
                            .or(Ok(0))
                    });
                }
                None => println!("None Connection"),
            };
        });
    }
}
