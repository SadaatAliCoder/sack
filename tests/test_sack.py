import unittest
from pathlib import Path
from sack.cli import (
    extract,
    _svelte_extract,
    _extract_tauri_calls,
    _other_extract,
    build_dependency_graph,
    _module_candidates,
    is_generated_or_minified,
    ScanResult,
)

class TestSACK(unittest.TestCase):
    def test_svelte4_props_and_tauri(self):
        source = """
<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import { invoke } from '@tauri-apps/api/core';
  import { listen } from '@tauri-apps/api/event';
  import Button from './Button.svelte';
  import type { UserProfile } from '$lib/types';

  export let title: string;
  export let count: number = 0;
  export let isOpen = false;
  export let user: UserProfile | null = null;

  const dispatch = createEventDispatcher<{ save: { id: number }; close: void }>();

  let localState = 'hello';

  async function handleSave() {
    await invoke('save_user', { user });
    dispatch('save', { id: 1 });
  }

  export function reset() {
    count = 0;
  }

  onMount(async () => {
    const sys = await invoke<string>('get_system_info');
    await listen('download-progress', (event) => {
      console.log(event);
    });
  });
</script>

<style>
  .btn { color: red; }
</style>

<div class="btn">
  <h1>{title}</h1>
  <Button on:click={handleSave} />
</div>
"""
        res = extract(Path("src/components/MyComponent.svelte"), source)
        
        # Test imports
        self.assertTrue(any("invoke" in imp for imp in res["imports"]))
        self.assertTrue(any("Button.svelte" in imp for imp in res["imports"]))
        
        # Test Svelte 4 props
        self.assertTrue(any("[Prop] export let title: string" in g for g in res["globals"]))
        self.assertTrue(any("[Prop] export let count: number = 0" in g for g in res["globals"]))
        self.assertTrue(any("[Prop] export let isOpen = false" in g for g in res["globals"]))
        self.assertTrue(any("[Prop] export let user: UserProfile | null = null" in g for g in res["globals"]))
        
        # Test Tauri commands
        self.assertTrue(any("invoke('save_user', { user })" in g for g in res["globals"]))
        self.assertTrue(any("invoke<string>('get_system_info')" in g for g in res["globals"]))
        self.assertTrue(any("listen('download-progress')" in g for g in res["globals"]))
        
        # Test events
        self.assertTrue(any("[Event Emitted] 'save'" in g for g in res["globals"]))
        
        # Test functions
        self.assertTrue(any("async function handleSave()" in s for s in res["signatures"]))
        self.assertTrue(any("export function reset()" in s for s in res["signatures"]))

    def test_svelte5_runes_props_state(self):
        source = """
<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';
  import Header from '$lib/Header.svelte';

  interface Props {
    title: string;
    initialCount?: number;
    onClose?: () => void;
  }

  let { title, initialCount = 0, onClose }: Props = $props();

  let count = $state(0);
  let doubled = $derived(count * 2);

  async function increment() {
    count += 1;
    await invoke('log_metric', { count, doubled });
  }
</script>

<div>
  <Header {title} />
  <button onclick={increment}>{count} / {doubled}</button>
</div>
"""
        res = extract(Path("src/routes/+page.svelte"), source)
        
        # Test Rune $props
        self.assertTrue(any("[Rune $props] let { title, initialCount = 0, onClose }: Props = $props()" in g for g in res["globals"]))
        
        # Test Runes $state and $derived
        self.assertTrue(any("[Rune] let count = $state(0)" in g for g in res["globals"]))
        self.assertTrue(any("[Rune] let doubled = $derived(count * 2)" in g for g in res["globals"]))
        
        # Test Tauri call
        self.assertTrue(any("invoke('log_metric', { count, doubled })" in g for g in res["globals"]))
        
        # Test Interface signature
        self.assertTrue(any("interface Props" in s for s in res["signatures"]))
        
        # Test function signature
        self.assertTrue(any("async function increment()" in s for s in res["signatures"]))

    def test_rust_tauri_command_attributes(self):
        source = """
use tauri::State;

#[tauri::command]
pub async fn greet(name: &str) -> Result<String, String> {
    Ok(format!("Hello, {}!", name))
}
"""
        res = extract(Path("src-tauri/src/main.rs"), source)
        self.assertTrue(any("#[tauri::command]" in s and "pub async fn greet" in s for s in res["signatures"]))

    def test_svelte_dependency_graph(self):
        files = {
            "src/components/Button.svelte": {"imports": []},
            "src/App.svelte": {
                "imports": [
                    "import Button from './components/Button.svelte';",
                    "import { invoke } from '@tauri-apps/api/core';",
                ]
            },
            "src/Header.svelte": {
                "imports": [
                    "import Button from '$lib/Button.svelte';",
                ]
            }
        }
        graph = build_dependency_graph(files)
        self.assertIn("src/components/Button.svelte", graph["src/App.svelte"])
        self.assertIn("src/components/Button.svelte", graph["src/Header.svelte"])

    def test_dart_flutter_extraction(self):
        source = """
import 'package:flutter/material.dart';
import 'package:my_app/models/user.dart';
import '../services/api_service.dart';
part 'home_screen.g.dart';

const String appTitle = 'My Flutter App';
final api = ApiService();
late final DatabaseClient db = DatabaseClient();

@immutable
abstract class BaseWidget extends StatelessWidget {
  const BaseWidget({super.key});
}

class HomeScreen extends StatefulWidget {
  final String title;
  const HomeScreen({super.key, required this.title});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _counter = 0;

  Future<void> _incrementCounter() async {
    _counter++;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: Container());
  }
}

enum AppTheme { light, dark, system }

typedef JsonMap = Map<String, dynamic>;
"""
        res = extract(Path("lib/screens/home_screen.dart"), source)

        # Test imports
        self.assertTrue(any("package:flutter/material.dart" in imp for imp in res["imports"]))
        self.assertTrue(any("package:my_app/models/user.dart" in imp for imp in res["imports"]))
        self.assertTrue(any("part 'home_screen.g.dart'" in imp for imp in res["imports"]))

        # Test globals / constants
        self.assertTrue(any("const String appTitle" in g for g in res["globals"]))
        self.assertTrue(any("final api = ApiService()" in g for g in res["globals"]))

        # Test signatures
        self.assertTrue(any("class HomeScreen extends StatefulWidget" in s for s in res["signatures"]))
        self.assertTrue(any("const HomeScreen({super.key, required this.title})" in s for s in res["signatures"]))
        self.assertTrue(any("@override" in s and "Widget build(BuildContext context)" in s for s in res["signatures"]))
        self.assertTrue(any("Future<void> _incrementCounter() async" in s for s in res["signatures"]))
        self.assertTrue(any("enum AppTheme" in s for s in res["signatures"]))
        self.assertTrue(any("typedef JsonMap" in s for s in res["signatures"]))

    def test_dart_dependency_graph(self):
        files = {
            "lib/models/user.dart": {"imports": []},
            "lib/services/api_service.dart": {"imports": []},
            "lib/screens/home_screen.dart": {
                "imports": [
                    "import 'package:flutter/material.dart';",
                    "import 'package:my_app/models/user.dart';",
                    "import '../services/api_service.dart';",
                    "part 'home_screen.g.dart';",
                ]
            }
        }
        graph = build_dependency_graph(files)
        self.assertIn("lib/models/user.dart", graph["lib/screens/home_screen.dart"])
        self.assertIn("lib/services/api_service.dart", graph["lib/screens/home_screen.dart"])

    def test_csharp_extraction(self):
        source = """
using System;
using Microsoft.AspNetCore.Mvc;

namespace MyApp.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UserController : ControllerBase
{
    private static readonly int MaxLimit = 50;

    [HttpGet("{id}")]
    public async Task<IActionResult> GetUser(int id)
    {
        return Ok(id);
    }
}

public interface IUserService
{
    Task<string> GetNameAsync(int id);
}

public record UserDto(string Name, int Age);
"""
        res = extract(Path("Controllers/UserController.cs"), source)
        self.assertTrue(any("using Microsoft.AspNetCore.Mvc;" in imp for imp in res["imports"]))
        self.assertTrue(any("namespace MyApp.Controllers;" in imp for imp in res["imports"]))
        self.assertTrue(any("MaxLimit = 50;" in g for g in res["globals"]))
        self.assertTrue(any("[ApiController]" in s and "public class UserController" in s for s in res["signatures"]))
        self.assertTrue(any("[HttpGet(\"{id}\")]" in s and "public async Task<IActionResult> GetUser(int id)" in s for s in res["signatures"]))
        self.assertTrue(any("public interface IUserService" in s for s in res["signatures"]))
        self.assertTrue(any("public record UserDto" in s for s in res["signatures"]))

    def test_kotlin_extraction(self):
        source = """
package com.example.myapp

import android.os.Bundle
import androidx.compose.runtime.Composable

const val API_VERSION = "v1"

@Serializable
data class User(val id: Int, val name: String)

class MainActivity : ComponentActivity() {
    @Composable
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }

    suspend fun fetchData(endpoint: String): String {
        return "data"
    }
}
"""
        res = extract(Path("app/src/main/MainActivity.kt"), source)
        self.assertTrue(any("package com.example.myapp" in imp for imp in res["imports"]))
        self.assertTrue(any("import android.os.Bundle" in imp for imp in res["imports"]))
        self.assertTrue(any("const val API_VERSION = \"v1\"" in g for g in res["globals"]))
        self.assertTrue(any("@Serializable" in s and "data class User" in s for s in res["signatures"]))
        self.assertTrue(any("@Composable" in s and "override fun onCreate" in s for s in res["signatures"]))
        self.assertTrue(any("suspend fun fetchData" in s for s in res["signatures"]))

    def test_swift_extraction(self):
        source = """
import SwiftUI
import Foundation

let AppVersion = "1.0.0"

protocol DataService {
    func fetchData() async throws -> [String]
}

struct ContentView: View {
    @State private var count: Int = 0

    init(initialCount: Int) {
        _count = State(initialValue: initialCount)
    }

    func increment() {
        count += 1
    }
}
"""
        res = extract(Path("Sources/Views/ContentView.swift"), source)
        self.assertTrue(any("import SwiftUI" in imp for imp in res["imports"]))
        self.assertTrue(any("let AppVersion = \"1.0.0\"" in g for g in res["globals"]))
        self.assertTrue(any("protocol DataService" in s for s in res["signatures"]))
        self.assertTrue(any("func fetchData() async throws -> [String]" in s for s in res["signatures"]))
        self.assertTrue(any("struct ContentView: View" in s for s in res["signatures"]))
        self.assertTrue(any("init(initialCount: Int)" in s for s in res["signatures"]))
        self.assertTrue(any("func increment()" in s for s in res["signatures"]))

    def test_ruby_extraction(self):
        source = """
require 'date'
require_relative 'base_service'

MAX_RETRIES = 5

module Authenticatable
  def authenticate(user)
    true
  end
end

class UsersController < ApplicationController
  def index
    @users = []
  end

  def self.find_user(id)
    nil
  end
end
"""
        res = extract(Path("app/controllers/users_controller.rb"), source)
        self.assertTrue(any("require 'date'" in imp for imp in res["imports"]))
        self.assertTrue(any("require_relative 'base_service'" in imp for imp in res["imports"]))
        self.assertTrue(any("MAX_RETRIES = 5" in g for g in res["globals"]))
        self.assertTrue(any("module Authenticatable" in s for s in res["signatures"]))
        self.assertTrue(any("def authenticate(user)" in s for s in res["signatures"]))
        self.assertTrue(any("class UsersController < ApplicationController" in s for s in res["signatures"]))
        self.assertTrue(any("def index" in s for s in res["signatures"]))
        self.assertTrue(any("def self.find_user(id)" in s for s in res["signatures"]))

    def test_generated_and_minified_filter(self):
        self.assertTrue(is_generated_or_minified("app.min.js"))
        self.assertTrue(is_generated_or_minified("styles.min.css"))
        self.assertTrue(is_generated_or_minified("user.g.dart"))
        self.assertTrue(is_generated_or_minified("user.freezed.dart"))
        self.assertTrue(is_generated_or_minified("user.mocks.dart"))
        self.assertTrue(is_generated_or_minified("Settings.Designer.cs"))
        self.assertTrue(is_generated_or_minified("MainWindow.g.i.cs"))
        self.assertTrue(is_generated_or_minified("schema.pb.go"))
        self.assertTrue(is_generated_or_minified("api.gen.go"))
        self.assertTrue(is_generated_or_minified("api_gen.go"))
        self.assertTrue(is_generated_or_minified("service_pb2.py"))
        self.assertTrue(is_generated_or_minified("moc_window.cpp"))
        self.assertTrue(is_generated_or_minified("window.moc.cpp"))
        # Real source code should NOT be ignored
        self.assertFalse(is_generated_or_minified("main.dart"))
        self.assertFalse(is_generated_or_minified("app.js"))
        self.assertFalse(is_generated_or_minified("UserController.cs"))
        self.assertFalse(is_generated_or_minified("index.py"))
        self.assertFalse(is_generated_or_minified("widget.cpp"))

    def test_csharp_rust_dependency_graph(self):
        files = {
            "Models/User.cs": {"imports": []},
            "Controllers/UserController.cs": {
                "imports": [
                    "using MyApp.Models.User;",
                    "using System;",
                ]
            },
            "src/models/item.rs": {"imports": []},
            "src/handlers/item_handler.rs": {
                "imports": [
                    "use crate::models::item;",
                ]
            }
        }
        graph = build_dependency_graph(files)
        self.assertIn("Models/User.cs", graph["Controllers/UserController.cs"])
        self.assertIn("src/models/item.rs", graph["src/handlers/item_handler.rs"])

    def test_scan_result_stats_and_unpacking(self):
        res = ScanResult(5, ["warning"], False, {"tokens": 1200, "lines": 80, "bytes": 3500, "total_files": 5})
        # Test backward-compatible 3-element unpack
        scanned, warnings, changed = res
        self.assertEqual(scanned, 5)
        self.assertEqual(warnings, ["warning"])
        self.assertFalse(changed)
        # Test stats exposure
        self.assertEqual(res.stats["tokens"], 1200)
        self.assertEqual(res.stats["lines"], 80)

if __name__ == "__main__":
    unittest.main()
