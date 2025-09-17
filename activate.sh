# activate.sh
#!/bin/bash

# Activate virtual environment
source ./my_env/Scripts/activate

# Alias python3 to the correct interpreter
alias python3='./my_env/Scripts/python.exe'

echo "Environment activated. You can now use python3 and run Django commands."