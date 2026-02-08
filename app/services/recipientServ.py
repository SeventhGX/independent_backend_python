from app.models.article import recipientBody
from app.models.tables.databaseTables import Recipient
from app.repositories import recipientRepo


async def get_all_recipients():
    recipients = recipientRepo.select_all_recipients()
    return {"data": recipients}


async def add_recipient(recipient: Recipient):
    # recipient = Recipient(email=re.email, name=re.name)
    new_recipient = recipientRepo.insert_recipient(recipient)
    return {"data": new_recipient}
