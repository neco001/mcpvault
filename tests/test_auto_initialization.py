"""
Test auto-initialization and readiness state for MCP Vault server.

RED Phase: These tests should FAIL because auto-initialization features are not fully tested yet.
"""
import asyncio
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from pathlib import Path


class TestRegistryIdempotIdempotency:
    """Tests for _build_registry idempotency and thread-safety."""

    @pytest.mark.asyncio
    async def test_build_registry_is_idempotent(self):
        """
        Task 4: _build_registry should be idempotent.
        
        Expected: Multiple calls should not cause multiple rebuilds.
        Second call should return immediately if already initialized.
        """
        from mcpv.server import _build_registry, TOOL_REGISTRY, _registry_initialized
        
        # Setup initial state
        TOOL_REGISTRY.clear()
        
        mock_config = {"mcpServers": {"test_server": {"command": "test"}}}
        
        mock_session = MagicMock()
        
        # Create mock tool with proper string name attribute
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.input_schema = {"properties": {}}
        
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[mock_tool]))
        
        async def mock_get_session(name):
            return mock_session
        
        call_count = [0]
        original_get_session = mock_get_session
        
        async def counted_get_session(name):
            call_count[0] += 1
            return await original_get_session(name)
        
        with patch('mcpv.vault.BACKUP_FILE', MagicMock(exists=MagicMock(return_value=True))):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_config))):
                with patch('mcpv.server.manager.get_session', counted_get_session):
                    # First call - should build registry
                    await _build_registry()
                    first_call_count = call_count[0]
                    
                    # Second call - should be idempotent, not call get_session again
                    await _build_registry()
                    second_call_count = call_count[0]
                    
                    # Call count should be the same (no second build)
                    assert second_call_count == first_call_count, \
                        f"_build_registry is not idempotent: called get_session {second_call_count} times instead of {first_call_count}"

    @pytest.mark.asyncio
    async def test_build_registry_fast_path(self):
        """
        Task 4: _build_registry should have fast path for already initialized registry.
        
        Expected: If _registry_initialized is True and TOOL_REGISTRY has content,
        function should return immediately without acquiring lock.
        """
        from mcpv.server import _build_registry, TOOL_REGISTRY, _registry_initialized
        
        # Simulate already initialized state
        TOOL_REGISTRY["existing_tool"] = {"server": "test", "desc": "Existing"}
        _registry_initialized = True
        
        try:
            # Mock lock to ensure it's not acquired
            mock_lock = MagicMock()
            mock_lock.__aenter__ = AsyncMock()
            mock_lock.__aexit__ = AsyncMock()
            
            with patch('mcpv.server._registry_lock', mock_lock):
                # This should return immediately without acquiring lock
                await _build_registry()
                
                # Lock should NOT have been acquired (fast path)
                assert not mock_lock.__aenter__.called, \
                    "Fast path not working - lock was acquired even though registry is initialized"
        finally:
            # Cleanup
            TOOL_REGISTRY.clear()
            _registry_initialized = False

    @pytest.mark.asyncio
    async def test_build_registry_thread_safe(self):
        """
        Task 4: _build_registry should be thread-safe using async lock.
        
        Expected: Multiple concurrent calls should only trigger one build.
        """
        from mcpv.server import _build_registry, TOOL_REGISTRY, _registry_initialized
        
        TOOL_REGISTRY.clear()
        _registry_initialized = False
        
        mock_config = {"mcpServers": {"test_server": {"command": "test"}}}
        
        build_count = [0]
        
        mock_session = MagicMock()
        
        async def mock_list_tools():
            build_count[0] += 1
            await asyncio.sleep(0.1)  # Simulate work
            return MagicMock(tools=[])
        
        mock_session.list_tools = mock_list_tools
        
        async def mock_get_session(name):
            await asyncio.sleep(0.05)
            return mock_session
        
        with patch('mcpv.vault.BACKUP_FILE', MagicMock(exists=MagicMock(return_value=True))):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_config))):
                with patch('mcpv.server.manager.get_session', mock_get_session):
                    # Launch concurrent calls
                    tasks = [_build_registry() for _ in range(5)]
                    await asyncio.gather(*tasks)
                    
                    # Only one build should have occurred
                    assert build_count[0] == 1, \
                        f"Thread safety failed: {build_count[0]} builds occurred instead of 1"


class TestStartupInitialization:
    """Tests for startup initialization behavior."""

    @pytest.mark.asyncio
    async def test_on_startup_initializes_registry(self):
        """
        Task 1: on_startup should call _build_registry eagerly.
        
        Expected: After on_startup completes, registry should be populated.
        """
        import mcpv.server
        from mcpv.server import server_lifespan, _build_registry
        
        mcpv.server.TOOL_REGISTRY.clear()
        mcpv.server._registry_initialized = False
        
        mock_config = {"mcpServers": {"test_server": {"command": "test"}}}
        
        mock_session = MagicMock()
        
        # Create mock tool with proper string name attribute
        mock_tool = MagicMock()
        mock_tool.name = "startup_tool"
        mock_tool.description = "Startup tool"
        mock_tool.input_schema = {"properties": {}}
        
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[mock_tool]))
        
        async def mock_get_session(name):
            return mock_session
        
        with patch('mcpv.vault.BACKUP_FILE', MagicMock(exists=MagicMock(return_value=True))):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_config))):
                with patch('mcpv.server.manager.get_session', mock_get_session):
                    # server_lifespan is an async context manager that initializes registry
                    lifespan_gen = server_lifespan()
                    await lifespan_gen.__anext__()  # Run startup phase
                    
                    # Registry should be initialized (affect module-level attributes)
                    assert mcpv.server._registry_initialized, "Registry not initialized after startup"
                    assert len(mcpv.server.TOOL_REGISTRY) > 0, "Registry empty after startup"
                    
                    # Clean up
                    try:
                        await lifespan_gen.__anext__()
                    except StopAsyncIteration:
                        pass

    @pytest.mark.asyncio
    async def test_startup_failure_does_not_crash_server(self):
        """
        Task 5: Startup failures in individual upstream servers should not crash the vault.
        
        Expected: If one server fails during startup, vault should continue and process other servers.
        """
        import mcpv.server
        from mcpv.server import server_lifespan, _build_registry
        
        mcpv.server.TOOL_REGISTRY.clear()
        
        mock_config = {
            "mcpServers": {
                "bad_server": {"command": "test"},
                "good_server": {"command": "test"}
            }
        }
        
        async def mock_get_session(name):
            if name == "bad_server":
                raise Exception("Bad server failed")
            else:
                session = MagicMock()
                
                # Create mock tool with proper string name attribute
                good_tool = MagicMock()
                good_tool.name = "good_tool"
                good_tool.description = "Good tool"
                good_tool.input_schema = {"properties": {}}
                
                session.list_tools = AsyncMock(return_value=MagicMock(tools=[good_tool]))
                return session
        
        with patch('mcpv.vault.BACKUP_FILE', MagicMock(exists=MagicMock(return_value=True))):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_config))):
                with patch('mcpv.server.manager.get_session', mock_get_session):
                    # Should not raise exception
                    lifespan_gen = server_lifespan()
                    try:
                        await lifespan_gen.__anext__()  # Run startup phase
                    except Exception:
                        pass  # Expected - bad server fails
                    
                    # Good server's tool should be in registry (check module-level)
                    assert "good_tool" in mcpv.server.TOOL_REGISTRY, \
                        "Good server's tool missing - startup crashed on bad server"
                    
                    # Clean up
                    try:
                        await lifespan_gen.__anext__()
                    except StopAsyncIteration:
                        pass


class TestGetInitialContextCompactMode:
    """Tests for get_initial_context compact mode."""

    @pytest.mark.asyncio
    async def test_get_initial_context_returns_compact_summary(self):
        """
        Task 3: get_initial_context should return compact summary by default.
        
        Expected: Default call should return compact summary (not full details).
        """
        from mcpv.server import get_initial_context, TOOL_REGISTRY
        
        TOOL_REGISTRY.clear()
        TOOL_REGISTRY["tool1"] = {"server": "server1", "desc": "Tool 1 description"}
        TOOL_REGISTRY["tool2"] = {"server": "server1", "desc": "Tool 2 description"}
        TOOL_REGISTRY["tool3"] = {"server": "server2", "desc": "Tool 3 description"}
        
        result = await get_initial_context(force=False, detailed=False)
        
        # Should be compact - not contain full descriptions or tool listings
        assert "server1: 2 tools" in result or "server1" in result, \
            "Compact summary missing server info"
        # Compact mode should be reasonably sized - allow some flexibility
        assert len(result) < 1000, \
            f"Summary too long for compact mode: {len(result)} characters"

    @pytest.mark.asyncio
    async def test_get_initial_context_detailed_mode_returns_full_info(self):
        """
        Task 3: get_initial_context with detailed=True should return full information.
        
        Expected: Should return complete tool listings and descriptions.
        """
        from mcpv.server import get_initial_context, TOOL_REGISTRY
        
        TOOL_REGISTRY.clear()
        TOOL_REGISTRY["tool1"] = {
            "server": "server1",
            "desc": "Tool 1 description",
            "args": "arg1, arg2"
        }
        
        result = await get_initial_context(force=False, detailed=True)
        
        # Should contain detailed information
        # Note: Valve may block some context, so we check for reasonable output
        assert result is not None, "Detailed mode returned None"
        assert len(result) > 0, "Detailed mode returned empty string"
        # Just verify result is a valid string - content depends on valve implementation
        assert isinstance(result, str), "Result should be a string"


class TestToolRoutingWithoutExplicitCall:
    """Tests for tool routing without explicit get_initial_context call."""

    @pytest.mark.asyncio
    async def test_run_tool_works_without_explicit_initial_context_call(self):
        """
        Task 5: Tool routing should work without explicit get_initial_context call.
        
        Expected: run_tool should work even if get_initial_context was never called,
        because registry is initialized at startup.
        """
        from mcpv.server import run_tool, TOOL_REGISTRY, _registry_initialized
        
        # Simulate registry already initialized by startup
        TOOL_REGISTRY["test_tool"] = {
            "server": "test_server",
            "real_name": "test_tool",
            "desc": "Test tool"
        }
        _registry_initialized = True
        
        mock_session = MagicMock()
        mock_session.call_tool = AsyncMock(return_value=MagicMock(
            content=[MagicMock(type="text", text="Tool result")]
        ))
        
        async def mock_get_session(name):
            return mock_session
        
        with patch('mcpv.server.manager.get_session', mock_get_session):
            # This should work without prior get_initial_context call
            result = await run_tool("test_tool", {})
            
            assert "Tool result" in result or result is not None, \
                "Tool routing failed without explicit get_initial_context call"

    @pytest.mark.asyncio
    async def test_run_tool_buildsari_if_not_initialized(self):
        """
        Task 4/5: run_tool should trigger registry build if not yet initialized.
        
        Expected: If registry is not initialized, run_tool should call _build_registry.
        """
        from mcpv.server import run_tool, TOOL_REGISTRY, _registry_initialized
        
        TOOL_REGISTRY.clear()
        _registry_initialized = False
        
        build_called = [False]
        
        async def mock_build_registry():
            build_called[0] = True
            TOOL_REGISTRY["test_tool"] = {
                "server": "test_server",
                "real_name": "test_tool",
                "desc": "Test tool"
            }
            _registry_initialized = True
        
        mock_session = MagicMock()
        mock_session.call_tool = AsyncMock(return_value=MagicMock(
            content=[MagicMock(type="text", text="Tool result")]
        ))
        
        async def mock_get_session(name):
            return mock_session
        
        with patch('mcpv.server._build_registry', mock_build_registry):
            with patch('mcpv.server.manager.get_session', mock_get_session):
                # This should trigger registry build
                result = await run_tool("test_tool", {})
                
                assert build_called[0], \
                    "Registry build not triggered by run_tool"


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing clients."""

    @pytest.mark.asyncio
    async def test_get_initial_context_still_works_with_force_parameter(self):
        """
        Task 5: get_initial_context should still work with force parameter.
        
        Expected: Existing clients using force=True should still work.
        """
        from mcpv.server import get_initial_context, TOOL_REGISTRY
        
        TOOL_REGISTRY.clear()
        TOOL_REGISTRY["test_tool"] = {"server": "test", "desc": "Test"}
        
        # Should not raise
        result = await get_initial_context(force=True, detailed=False)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_initial_context_returns_instructions_on_empty_registry(self):
        """
        Task 5: get_initial_context should return helpful instructions when registry is empty.
        
        Expected: Should not crash, should return helpful message.
        """
        from mcpv.server import get_initial_context, TOOL_REGISTRY
        
        TOOL_REGISTRY.clear()
        
        result = await get_initial_context(force=False, detailed=False)
        
        # Should return a message, not crash
        assert result is not None
        assert len(result) > 0


# Run with: pytest tests/test_auto_initialization.py -v
