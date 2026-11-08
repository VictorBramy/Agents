{ pkgs, ... }: {
  channel = "stable-24.11";

  packages = [
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.python3Packages.virtualenv

    # Nix wrapper binaries so IDX backend daemon can immediately find pip3 and pip in $PATH
    (pkgs.writeShellScriptBin "pip3" ''
      #!/usr/bin/env bash
      if [ -f "$PWD/.venv/bin/pip" ]; then
        exec "$PWD/.venv/bin/pip" "$@"
      elif [ -f "./.venv/bin/pip" ]; then
        exec "./.venv/bin/pip" "$@"
      else
        ${pkgs.python3}/bin/python3 -m venv "$PWD/.venv" 2>/dev/null || true
        if [ -f "$PWD/.venv/bin/pip" ]; then
          exec "$PWD/.venv/bin/pip" "$@"
        else
          exec ${pkgs.python3}/bin/python3 -m pip "$@"
        fi
      fi
    '')

    (pkgs.writeShellScriptBin "pip" ''
      #!/usr/bin/env bash
      if [ -f "$PWD/.venv/bin/pip" ]; then
        exec "$PWD/.venv/bin/pip" "$@"
      elif [ -f "./.venv/bin/pip" ]; then
        exec "./.venv/bin/pip" "$@"
      else
        ${pkgs.python3}/bin/python3 -m venv "$PWD/.venv" 2>/dev/null || true
        if [ -f "$PWD/.venv/bin/pip" ]; then
          exec "$PWD/.venv/bin/pip" "$@"
        else
          exec ${pkgs.python3}/bin/python3 -m pip "$@"
        fi
      fi
    '')

    # System libraries required for Playwright Chromium headless
    pkgs.nspr
    pkgs.nss
    pkgs.atk
    pkgs.cups
    pkgs.dbus
    pkgs.libdrm
    pkgs.libxkbcommon
    pkgs.pango
    pkgs.cairo
    pkgs.glib
    pkgs.gtk3
    pkgs.mesa
    pkgs.expat
    pkgs.alsa-lib
    pkgs.at-spi2-atk
    pkgs.xorg.libX11
    pkgs.xorg.libXcomposite
    pkgs.xorg.libXcursor
    pkgs.xorg.libXdamage
    pkgs.xorg.libXext
    pkgs.xorg.libXfixes
    pkgs.xorg.libXi
    pkgs.xorg.libXrandr
    pkgs.xorg.libXrender
    pkgs.xorg.libxcb
  ];

  env = {
    PYTHONUNBUFFERED = "1";
    PORT = "8080";
  };

  idx = {
    extensions = [
      "ms-python.python"
      "ms-python.vscode-pylance"
    ];

    workspace = {
      onCreate = {
        setup = ''
          python3 -m venv .venv
          source .venv/bin/activate
          pip install --upgrade pip
          pip install -r requirements.txt
          playwright install chromium
          if [ ! -f .env ]; then
            cp .env.example .env
          fi
        '';
      };
      onStart = {
        ensure-env = ''
          if [ ! -f .env ]; then
            cp .env.example .env
          fi
          if [ ! -d .venv ]; then
            python3 -m venv .venv
            source .venv/bin/activate
            pip install -r requirements.txt
            playwright install chromium
          fi
        '';
      };
    };

    previews = {
      enable = true;
      previews = {
        web = {
          command = [
            "bash"
            "-c"
            "if [ ! -d .venv ]; then python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && playwright install chromium; else source .venv/bin/activate; fi && python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT"
          ];
          manager = "web";
        };
      };
    };
  };
}
