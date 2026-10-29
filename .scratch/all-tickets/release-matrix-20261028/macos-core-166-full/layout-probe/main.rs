#[allow(dead_code)]
enum LexErrorShape {
    UnexpectedInput(String),
    UnterminatedString,
    StringTooLong(usize),
    MalformedEscapeSequence(String),
    MalformedNumber(String),
    MalformedChar(String),
    MalformedIdentifier(String),
    ImproperSymbol(String, String),
    Runtime(String),
}
fn main() { println!("{}", std::mem::size_of::<LexErrorShape>()); }
