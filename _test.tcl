set verify

set tree mgttest /shot=-1
create pulse 42

set tree mgttest /shot=42
do /meth ACQ init
