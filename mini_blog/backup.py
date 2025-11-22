import shutil
import datetime

now = datetime.datetime.now().strftime("%Y%m%d-%H%M")
shutil.copy("database.db", f"backup-{now}.db")
print("Backup thành công!")