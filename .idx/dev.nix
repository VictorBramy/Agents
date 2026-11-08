{ pkgs, ... }: {
  channel = "stable-24.11";

  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv

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
    };

    previews = {
      enable = true;
      previews = {
        web = {
          command = [
            "bash"
            "-c"
            "source .venv/bin/activate && python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT"
          ];
          manager = "web";
        };
      };
    };
  };
}
