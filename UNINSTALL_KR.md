# 🗑️ MCP Vault (`mcpv`) 제거 및 원상복구 가이드

`mcpv`를 제거하고 Antigravity 에이전트를 원래 상태로 복구하는 방법입니다.

## 🛠️ 자동 제거 (권장)
제공된 `uninstall.ps1` 스크립트를 사용하여 자동으로 백업된 설정을 복구하고 관련 파생 파일들을 깔끔하게 삭제할 수 있습니다.

```powershell
# PowerShell을 열고 다운로드 받은 저장소 폴더 내에서 다음을 실행하세요:
.\uninstall.ps1
```

---

## 🖐️ 수동 제거 방법
스크립트를 사용할 수 없거나 수동으로 완전히 지우고 싶을 경우 다음 3단계를 순서대로 따르세요.

### 1단계: 패키지 삭제
PowerShell 또는 명령 프롬프트를 열고 설치된 `mcpv` 패키지를 제거합니다.
```powershell
uv pip uninstall mcpv
# uv를 사용하지 않았다면: pip uninstall mcpv
```

### 2단계: 바탕화면 바로가기 삭제
바탕화면에 있는 **`Antigravity Boost (mcpv)`** 바로가기 아이콘을 삭제합니다. 
이후부터는 원래 쓰시던 기본 Antigravity 단축아이콘을 통해 실행하시면 됩니다.

### 3단계: 기존 설정(Config) 복구 및 찌꺼기 파일 제거
`mcpv`가 남긴 프록시 설정을 지우고 기존 백업을 살리는 과정입니다.

1. 파일 탐색기를 열고 주소창에 `%USERPROFILE%\.gemini\antigravity` 를 입력한 후 엔터를 칩니다.
   *(일반적으로 `C:\Users\사용자이름\.gemini\antigravity` 경로입니다.)*
2. 해당 폴더에서 다음 3개의 파일을 찾아 **삭제**합니다:
   - `mcp_config.json` (mcpv가 덮어씌웠던 프록시 설정)
   - `boost_launcher.bat` (부스터 스크립트)
   - `root_path.txt` (고정된 프로젝트 경로)
3. **원본 설정 파일 복구**:
   - 같은 폴더에 있는 **`mcp_config.original.json`** 파일의 이름을 **`mcp_config.json`** 으로 변경합니다.
   
> 💡 *참고: 만약 기존에 설정했던 MCP가 아예 없었다면 `mcp_config.original.json` 파일이 존재하지 않을 수 있습니다. 이 경우 원래 설정이 비어있던 것이므로, 기존 `mcp_config.json`을 삭제하는 것만으로 충분히 원상복구 됩니다.*

---

## 💡 WSL (Windows Subsystem for Linux) 호환성 관련 안내

`mcpv`는 Windows 시스템 환경(경로 및 레지스트리, 바로가기 생성, Windows Antigravity 경로 하드코딩 등)에 특화되어 제작되었습니다. 

WSL 커널 내부에서 `mcpv install`을 실행할 경우, WSL 상의 리눅스 경로와 Windows 런타임 간의 괴리로 인해 `mcp_config.json` 백업 및 연동에 문제가 발생하거나 데스크톱 바로가기가 생성되지 않는 등의 제한이 있습니다.

현재 버전에서는 **Windows 환경의 PowerShell이나 Command Prompt(혹은 VSCode의 Windows 터미널)에서 설치 및 실행**하는 것을 적극 권장합니다.
