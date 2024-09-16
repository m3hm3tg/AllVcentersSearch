import sys
import json
import ssl
from PyQt5 import QtWidgets
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from prettytable import PrettyTable

# Global değişkenler
user = None
pwd = None

# Kullanıcı adı ve şifreyi al
def get_credentials():
    global user, pwd
    app = QtWidgets.QApplication(sys.argv)

    # Kullanıcı girişi penceresi
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("vCenter Girişi")

    layout = QtWidgets.QFormLayout()
    
    user_input = QtWidgets.QLineEdit()
    user_input.setPlaceholderText("vCenter Kullanıcı Adı")
    pwd_input = QtWidgets.QLineEdit()
    pwd_input.setPlaceholderText("vCenter Şifresi")
    pwd_input.setEchoMode(QtWidgets.QLineEdit.Password)
    
    layout.addRow("Kullanıcı Adı:", user_input)
    layout.addRow("Şifre:", pwd_input)
    
    button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    
    layout.addWidget(button_box)
    dialog.setLayout(layout)

    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        user = user_input.text()
        pwd = pwd_input.text()
    
    if not user or not pwd:
        QtWidgets.QMessageBox.critical(None, "Hata", "Kullanıcı adı veya şifre girilmedi!")
        sys.exit()

# vCenter bağlantılarını sağlamak için
def connect_to_vcenter(host):
    try:
        context = ssl._create_unverified_context()
        si = SmartConnect(host=host, user=user, pwd=pwd, sslContext=context)
        return si
    except Exception as e:
        print(f"Could not connect to {host}: {e}")
        return None

# JSON dosyasından vCenter adreslerini al
def get_vcenter_connections():
    with open("VCENTERLAR.json", "r") as file:
        credentials = json.load(file)
    
    connections = []
    for vc in credentials["vcenters"]:
        host = vc["host"]
        si = connect_to_vcenter(host)
        if si:
            connections.append((host, si))
    return connections

# VM bilgilerini getir
def get_vm_info(vm, vc_host):
    ip_addresses = "\n".join(
        [ip for net in vm.guest.net for ip in net.ipAddress if ip and not ip.startswith("fe80")]
    ) if vm.guest.net else "Bulunamadı"

    vm_info = {
        "vCenter": vc_host,
        "VM Name": vm.name,
        "VM Path": vm.summary.config.vmPathName,
        "Network": ", ".join([net.name for net in vm.network]) if vm.network else "N/A",
        "CPU": vm.config.hardware.numCPU,
        "RAM (GB)": vm.config.hardware.memoryMB // 1024,
        "HDD (GB)": sum([disk.capacityInKB for disk in vm.config.hardware.device if isinstance(disk, vim.vm.device.VirtualDisk)]) // (1024 * 1024),
        "IP Addresses": ip_addresses,
        "Power State": "ON" if vm.runtime.powerState == "poweredOn" else "OFF"
    }
    return vm_info

# İsimle VM araması yap
def search_vms_by_name(vm_name):
    connections = get_vcenter_connections()
    results = []

    for vc_host, si in connections:
        content = si.RetrieveContent()
        container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
        for vm in container.view:
            if vm_name.lower() in vm.name.lower():
                results.append(get_vm_info(vm, vc_host))
        container.Destroy()
        Disconnect(si)

    return results

# Ana program
def main():
    print("vCenter VM Arama Scriptine Hoşgeldiniz. M.G.")
    
    # İlk açılışta kullanıcı adı ve şifre alınacak
    get_credentials()

    while True:
        search_term = input("VM adı veya içinde geçen bir değer gir: ")

        # En az 3 karakter uzunluğunda bir arama terimi girilmesini sağla
        if len(search_term) < 3:
            print("Arama terimi en az 3 karakter olmalıdır. Lütfen tekrar deneyin.")
            continue

        results = search_vms_by_name(search_term)

        if results:
            table = PrettyTable()
            table.field_names = ["vCenter", "VM Name", "VM Path", "Network", "CPU", "RAM (GB)", "HDD (GB)", "IP Addresses", "Power State"]

            for result in results:
                table.add_row([
                    result["vCenter"],
                    result["VM Name"],
                    result["VM Path"],
                    result["Network"],
                    result["CPU"],
                    result["RAM (GB)"],
                    result["HDD (GB)"],
                    result["IP Addresses"],
                    result["Power State"]
                ])

            print(table)
        else:
            print("Sonuç bulunamadı.")

        # Yeni arama yapmak için döngüye geri dön
        # Burada kullanıcıya yeni arama yapma isteği sorulmayacak, sadece döngüye geri dönecek

if __name__ == "__main__":
    main()
