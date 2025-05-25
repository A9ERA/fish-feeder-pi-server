import serial.tools.list_ports

ports = serial.tools.list_ports.comports()
for port in ports:
    if "Arduino" in port.description or "Mega" in port.description:
        print("Found Arduino at:", port.device)
        # เปิดพอร์ตได้เลย
        ser = serial.Serial(port.device, 9600)
        break
