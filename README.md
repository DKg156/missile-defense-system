# missile-defense-system

### Build command: (For autogenerating proto files)
```
python -m grpc_tools.protoc -I./protos --python_out=. --pyi_out=. --grpc_python_out=. ./protos/helloworld.proto
```

### Run command:
Server:
```
python greeter_server.py
```

Client:
```
python greeter_client.py
```