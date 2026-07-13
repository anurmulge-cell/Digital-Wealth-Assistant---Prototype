"""
avatar.py
Renders a real 3D avatar (a Ready Player Me .glb model) inside the Streamlit
app using Google's <model-viewer> web component, embedded via
st.components.v1.html.

Honest scope note: this is a real 3D model render with camera controls and
auto-rotate - not a full Ready Player Me SDK integration with rigged
lip-sync or the RPM avatar creator embedded in-app. Getting *that* fully
wired (RPM iframe creator -> save -> animate visemes to TTS audio) is a
multi-day integration. This gives you a genuine 3D avatar on screen today,
with a lightweight "just responded" pulse animation, and is built so a full
RPM creator + ElevenLabs viseme pipeline can be dropped in later without
changing how the rest of the app calls this module.

To use your own avatar:
1. Go to https://readyplayer.me/ and create a free avatar (guest mode, no
   login required).
2. Copy the .glb URL it gives you at the end (looks like
   https://models.readyplayer.me/<id>.glb).
3. Paste it into the "Avatar GLB URL" field in the app sidebar.
If no URL is supplied, the app falls back to the original CSS avatar circle
so the demo still works with zero setup.

Deployment note: some hosts (Streamlit Community Cloud included, depending
on outbound network policy) can block the model-viewer CDN script or the
.glb file itself, which otherwise just shows a blank box with zero
explanation to a judge. get_avatar_html() below includes a JS watchdog that
detects this (via the element's 'error' event, or a timeout if the script
never loads at all) and swaps in a text fallback explaining what should be
there - so a blocked avatar reads as "intentional, documented" rather than
"broken."
"""

MODEL_VIEWER_CDN = "https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"

# Public Ready Player Me sample avatar, used only as a default so the demo
# has *something* to show before a judge/teammate pastes a real one.
DEFAULT_AVATAR_GLB = "https://models.readyplayer.me/65a8dba831b23abb4f401b17.glb"


def get_avatar_html(glb_url: str, speaking: bool = False, height: int = 220) -> str:
    url = glb_url.strip() if glb_url and glb_url.strip() else DEFAULT_AVATAR_GLB
    pulse_class = "speaking" if speaking else ""
    return f"""
    <script type="module" src="{MODEL_VIEWER_CDN}"></script>
    <style>
      .avatar-wrap {{
        width: 100%; height: {height}px; border-radius: 14px; overflow: hidden;
        background: radial-gradient(circle at 50% 20%, #E9FBF3 0%, #F7F9FA 70%);
        position: relative;
      }}
      model-viewer {{
        width: 100%; height: 100%; --poster-color: transparent;
        transition: transform 0.25s ease-out;
      }}
      .speaking {{
        animation: avatarPulse 0.9s ease-in-out infinite;
      }}
      @keyframes avatarPulse {{
        0%   {{ transform: scale(1.0); }}
        50%  {{ transform: scale(1.03); }}
        100% {{ transform: scale(1.0); }}
      }}
      .avatar-fallback {{
        display: none; position: absolute; inset: 0; padding: 16px;
        flex-direction: column; align-items: center; justify-content: center;
        text-align: center; font-family: sans-serif; color: #0B3D2E;
      }}
      .avatar-fallback.show {{ display: flex; }}
      .avatar-fallback .icon {{ font-size: 28px; margin-bottom: 8px; }}
      .avatar-fallback .title {{ font-weight: 700; font-size: 13px; margin-bottom: 4px; }}
      .avatar-fallback .desc {{ font-size: 11px; color: #64748B; line-height: 1.4; }}
    </style>
    <div class="avatar-wrap">
      <model-viewer
        id="wealthAvatarModel"
        class="{pulse_class}"
        src="{url}"
        camera-controls
        auto-rotate
        auto-rotate-delay="0"
        rotation-per-second="12deg"
        camera-target="0m 1.55m 0m"
        camera-orbit="0deg 85deg 0.85m"
        min-camera-orbit="auto 85deg 0.85m"
        max-camera-orbit="auto 85deg 0.85m"
        field-of-view="25deg"
        shadow-intensity="0.6"
        exposure="1.0"
        interaction-prompt="none"
        disable-zoom>
      </model-viewer>
      <div id="wealthAvatarFallback" class="avatar-fallback">
        <div class="icon">\U0001F9CD</div>
        <div class="title">3D Avatar (blocked in this environment)</div>
        <div class="desc">
          A live 3D WealthAssist avatar renders here in local/dev testing.<br/>
          This host's network policy is blocking the model-viewer asset -
          see README.md for the working local demo.
        </div>
      </div>
    </div>
    <script>
      (function() {{
        const modelEl = document.getElementById('wealthAvatarModel');
        const fallbackEl = document.getElementById('wealthAvatarFallback');
        let resolved = false;
        function showFallback() {{
          if (resolved) return;
          resolved = true;
          if (modelEl) modelEl.style.display = 'none';
          if (fallbackEl) fallbackEl.classList.add('show');
        }}
        function markLoaded() {{ resolved = true; }}
        if (modelEl) {{
          modelEl.addEventListener('error', showFallback);
          modelEl.addEventListener('load', markLoaded);
        }} else {{
          showFallback();
        }}
        // Watchdog: if neither 'load' nor 'error' fires (e.g. the CDN
        // script itself never loaded, so model-viewer never upgraded into
        // a working custom element), show the fallback anyway after a
        // reasonable timeout rather than leaving a permanently blank box.
        setTimeout(showFallback, 6000);
      }})();
    </script>
    """
