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
    </style>
    <div class="avatar-wrap">
      <model-viewer
        class="{pulse_class}"
        src="{url}"
        camera-controls
        auto-rotate
        auto-rotate-delay="0"
        rotation-per-second="12deg"
        camera-orbit="0deg 80deg 2.2m"
        field-of-view="30deg"
        shadow-intensity="0.6"
        exposure="1.0"
        interaction-prompt="none"
        disable-zoom>
      </model-viewer>
    </div>
    """
