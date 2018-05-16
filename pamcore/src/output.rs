use std::collections::VecDeque;
use std::io::Error;
use std::net::TcpStream;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use std::thread;

use std::cell::RefCell;
use std::rc::Rc;
use backoff::{ExponentialBackoff, Operation};
use std::fmt::Display;
use std::io;
use backoff;
use native_tls::{TlsConnector, TlsStream};
use std::io::{Read, Write};

lazy_static! {
    pub static ref OUTPUT_QUEUE: Arc<Mutex<VecDeque<Vec<u8>>>> = {
        let vector: VecDeque<Vec<u8>> = VecDeque::new();
        Arc::new(Mutex::new(vector))
    };
}


fn get_connection(addr: &str) -> Result<TlsStream<TcpStream>, Error> {
    trace!("Try to connect to remote server.");
    let connector = TlsConnector::builder().unwrap().build().unwrap();
    trace!("TLSConnector is builded");
    let stream = TcpStream::connect(addr).map_err(new_io_err)?;
    info!("TCPStream is connect");
    let stream = connector.connect("pushamp.com", stream).map_err(new_io_err);
    trace!("Return TLS STREAM");
    stream
}
#[derive(Clone)]
pub struct PamCollectorOutput {
    addr: String,
    token: String,
}

pub trait Output {
    fn start(&self);
    fn recreate_stream(&self) -> Result<TlsStream<TcpStream>, backoff::Error<io::Error>>;
    fn consume_events(&self, shared_stream: Rc<RefCell<TlsStream<TcpStream>>>);
}

impl PamCollectorOutput {
    pub fn new(mut token: String, addr: String) -> PamCollectorOutput {
        token.push_str("\r\n");
        PamCollectorOutput { addr, token }
    }
}

fn new_io_err<E: Display>(err: E) -> io::Error {
    warn!("{}", err.to_string());
    io::Error::new(io::ErrorKind::Other, err.to_string())
}

impl Output for PamCollectorOutput {
    fn start(&self) {
        trace!("Handle PamCollectorOutput::start");
        match self.recreate_stream() {
            Ok(v) => {
                let shared_stream: Rc<RefCell<TlsStream<TcpStream>>> = Rc::new(RefCell::new(v));
                info!("Start consume events");
                self.consume_events(shared_stream);
            }
            Err(e) => warn!("Error while creating TCP Stream. Error: {}", e),
        };
    }

    fn recreate_stream(&self) -> Result<TlsStream<TcpStream>, backoff::Error<io::Error>> {
        let mut backoff = ExponentialBackoff::default();
        info!("BackOff configured");
        let mut op = || {
            let mut stream = get_connection(&self.addr).map_err(new_io_err)?;
            info!("Prepare write token");
            let status_w: Result<usize, Error> = stream.write(self.token.as_bytes());
            trace!("Write token payload to server. Write bytes: {:?}", status_w);
            status_w.map_err(new_io_err)?;
            let mut buffer: [u8; 10] = [0; 10];
            let stat: usize = stream.read(&mut buffer).map_err(new_io_err)?;
            fn check_stat(stat: usize) -> Result<(), io::Error> {
                match stat {
                    0 => {
                        warn!("Token invalid. Connection Close");
                        Err(Error::new(
                            io::ErrorKind::Other,
                            "Token invalid. Connection Close",
                        ))
                    }
                    _ => {
                        info!("Token Valid");
                        Ok(())
                    }
                }
            };
            check_stat(stat)
                .map_err(new_io_err)
                .map_err(backoff::Error::Permanent)?;
            Ok(stream)
        };
        op.retry(&mut backoff)
    }

    fn consume_events(&self, shared_stream: Rc<RefCell<TlsStream<TcpStream>>>) {
        info!("Consume event output loop started");
        let mut need_recreate: bool = true;
        let mut new_stream: TlsStream<TcpStream>;
        loop {
            trace!("In Loop");
            if need_recreate {
                trace!("TCP Stream need to recreate");
                thread::sleep(Duration::from_secs(10));
                match self.recreate_stream() {
                    Ok(v) => new_stream = v,
                    Err(e) => {
                        warn!("Error recreate stream. Error: {}", e);
                        need_recreate = true;
                        continue;
                    }
                };
                shared_stream.replace(new_stream);
                need_recreate = false;
            }
                    debug!("Get OUTPUT_QUEUE");
                    let val: Option<Vec<u8>> = OUTPUT_QUEUE.lock().unwrap().pop_front();
                    match val {
                        Some(mut v) => {
                            debug!("Start write bytes with payload");
                            v.append(&mut "\r\n".as_bytes().to_vec());
                            debug!("Prepare send payload");
                            debug!("Payload size is {}", v.len());
                            trace!("Value is {:?}", &v);
                            let _ = shared_stream.borrow_mut().write_all(&v);
                            info!("Start read bytes after write payload");
                            let read_bytes: Result<usize, Error> = shared_stream.borrow_mut().read(&mut [0; 128]);
                            match read_bytes {
                                Ok(v) => {
                                    match v {
                                        0 => {
                                            warn!("Remote server close connect");
                                            need_recreate = true;
                                        }
                                        _ => trace!("Success write trace payload"),
                                    };
                                }
                                Err(e) => {
                                    error!("Error while read payload response {}", e);
                                    need_recreate = true;
                                }
                            }
                        }
                        None => {
                            trace!("Not val");
                            thread::sleep(Duration::from_millis(400));
                            ()
                        }
                    }
        }
    }
}
