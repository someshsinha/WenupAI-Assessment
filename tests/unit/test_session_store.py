import asyncio
import pytest
from app.services.session_store import SessionStore
from app.domain.models import Message


@pytest.mark.asyncio
async def test_session_store_crud():
    store = SessionStore()

    # Create
    sess = await store.create()
    assert sess.id is not None
    assert sess.state.version == 0

    # Get
    fetched = await store.get(sess.id)
    assert fetched is not None
    assert fetched.id == sess.id

    # Save
    fetched.messages.append(Message(role="user", content="Hello", turn=1))
    await store.save(fetched)

    updated = await store.get(sess.id)
    assert len(updated.messages) == 1

    # Delete
    deleted = await store.delete(sess.id)
    assert deleted is True
    assert await store.get(sess.id) is None

    # Delete non-existent
    assert await store.delete("non_existent") is False


@pytest.mark.asyncio
async def test_per_session_locking_serializes_concurrent_updates():
    store = SessionStore()
    sess = await store.create("sess_concurrent")

    execution_order = []

    async def update_worker(worker_id: int, delay: float):
        async with store.lock(sess.id):
            execution_order.append(f"start_{worker_id}")
            current = await store.get(sess.id)
            await asyncio.sleep(delay)
            current.state.version += 1
            await store.save(current)
            execution_order.append(f"end_{worker_id}")

    # Launch two concurrent workers on the same session
    await asyncio.gather(
        update_worker(1, 0.05),
        update_worker(2, 0.02),
    )

    final = await store.get(sess.id)
    assert final.state.version == 2
    # Verify strict serialization (start_1 -> end_1 -> start_2 -> end_2 or vice versa, never interleaved)
    assert (
        execution_order == ["start_1", "end_1", "start_2", "end_2"]
        or execution_order == ["start_2", "end_2", "start_1", "end_1"]
    )


@pytest.mark.asyncio
async def test_independent_sessions_do_not_block():
    store = SessionStore()
    sess_a = await store.create("sess_a")
    sess_b = await store.create("sess_b")

    order = []

    async def worker_a():
        async with store.lock(sess_a.id):
            order.append("a_start")
            await asyncio.sleep(0.04)
            order.append("a_end")

    async def worker_b():
        async with store.lock(sess_b.id):
            order.append("b_start")
            await asyncio.sleep(0.01)
            order.append("b_end")

    await asyncio.gather(worker_a(), worker_b())

    # Worker B with shorter sleep should finish while A is still sleeping (interleaved start/end proves independent locks)
    assert "b_end" in order
    assert "a_end" in order
    # Because B only sleeps 0.01 vs A 0.04, B will finish before A finishes
    b_end_idx = order.index("b_end")
    a_end_idx = order.index("a_end")
    assert b_end_idx < a_end_idx
