from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


class CleaningAsyncSqliteSaver(AsyncSqliteSaver):
    async def aput(self, config, checkpoint, metadata, new_versions):
        """Save checkpoint with cleaned messages"""

        return await super().aput(config, checkpoint, metadata, new_versions)
