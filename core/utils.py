from functools import wraps

from datetime import datetime, timezone
import dateutil.parser
from natural.date import duration


def loglist():
    def decorator(func):
        @wraps(func)
        async def wrapper(request, page=1):
            app = request.app
            
            config = await app.ctx.db.config.find_one()

            collection = app.ctx.db.logs

            try:
                page = int(request.args.get("page", 1))
            except ValueError:
                page = 1

            def parse_date(date):
                date = dateutil.parser.parse(date).astimezone(timezone.utc)
                timestamp = duration(date, datetime.now(timezone.utc))
                return timestamp

            async def find():
                filter_ = {"bot_id": str(config["bot_id"])}
                projection_ = {
                    "_id": 1,
                    "key": 1,
                    "open": 1,
                    "created_at": 1,
                    "closed_at": 1,
                    "recipient": 1,
                    "creator": 1,
                    "title": 1,
                    "messages": 1,
                }

                cursor = collection.find(filter=filter_, projection=projection_, skip=(page-1)*25).sort(
                    "created_at", -1
                )

                count = await collection.count_documents(filter=filter_)
                max_page = (count % 25) + 1
                items = await cursor.to_list(length=25)

                # iterate over list to change timestamps to readable format
                for index, item in enumerate(items):
                    creation_date = item.get('created_at')
                    items[index].update(created_at=parse_date(creation_date))
                    close_date = item.get('closed_at')

                    if close_date is not None:
                        items[index].update(closed_at=parse_date(close_date))

                    messages = items[index].get('messages') # this returns the last message in array
                    last_message_duration = parse_date(messages[-1].get('timestamp'))
                    items[index]['last_message_time'] = last_message_duration


                return items, max_page

            document, max_page = await find()
            return await func(request, document, page, max_page)

        return wrapper

    return decorator
