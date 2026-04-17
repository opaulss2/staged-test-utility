from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tpms_utility.config import AppSettings, DltConnectionSettings
from tpms_utility.cycle_controller import CycleController
from tpms_utility.stages.profiles import discover_profiles, load_profile


class ProfilesTests(unittest.TestCase):
    def test_discover_profiles_finds_json_files(self) -> None:
        """Test that discover_profiles finds all .json files in stages directory."""
        profiles = discover_profiles()
        
        # Should find at least default_cycle.json
        self.assertGreater(len(profiles), 0)
        
        profile_names = [name for name, _ in profiles]
        self.assertIn("default_cycle", profile_names)

    def test_discover_profiles_returns_sorted_list(self) -> None:
        """Test that discover_profiles returns profiles sorted by name."""
        profiles = discover_profiles()
        
        profile_names = [name for name, _ in profiles]
        self.assertEqual(profile_names, sorted(profile_names))

    def test_discover_profiles_returns_valid_paths(self) -> None:
        """Test that discover_profiles returns valid file paths."""
        profiles = discover_profiles()
        
        for name, path in profiles:
            self.assertIsInstance(name, str)
            self.assertIsInstance(path, Path)
            self.assertTrue(path.exists())
            self.assertTrue(path.suffix == ".json")

    def test_load_profile_loads_default_cycle(self) -> None:
        """Test that load_profile can load the default cycle."""
        app_settings = AppSettings(output_root=Path(tempfile.gettempdir()))
        dlt_settings = DltConnectionSettings()
        
        controller = CycleController(
            stages=[],
            app_settings=app_settings,
            dlt_settings=dlt_settings,
            on_state_changed=lambda: None,
            on_log=lambda _: None,
            on_timer_changed=lambda _: None,
        )
        
        profiles = discover_profiles()
        default_profile = next((path for name, path in profiles if name == "default_cycle"), None)
        self.assertIsNotNone(default_profile)
        
        stages = load_profile(controller, default_profile)
        
        self.assertGreater(len(stages), 0)
        # Verify all stages have required attributes
        for stage in stages:
            self.assertIsNotNone(stage.stage_id)
            self.assertIsNotNone(stage.name)
            self.assertIsNotNone(stage.script_name)

    def test_load_profile_invalid_file_raises(self) -> None:
        """Test that load_profile raises for invalid profile file."""
        app_settings = AppSettings(output_root=Path(tempfile.gettempdir()))
        dlt_settings = DltConnectionSettings()
        
        controller = CycleController(
            stages=[],
            app_settings=app_settings,
            dlt_settings=dlt_settings,
            on_state_changed=lambda: None,
            on_log=lambda _: None,
            on_timer_changed=lambda _: None,
        )
        
        # Create a temporary invalid JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            temp_path = Path(f.name)
        
        try:
            with self.assertRaises(Exception):  # Could be json.JSONDecodeError or other
                load_profile(controller, temp_path)
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
