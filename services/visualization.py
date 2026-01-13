import io
import base64

def plot_pentagon(scores: list[float]) -> str:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")  # Use a non-GUI backend
    import matplotlib.pyplot as plt
    labels = ["Grammar", "Vocabulary", "Fluency", "Pronunciation", "Filler Words"]
    angles = np.linspace(0, 2 * np.pi, len(scores), endpoint=False).tolist()
    scores += scores[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
    ax.plot(angles, scores, "o-", linewidth=2)
    ax.fill(angles, scores, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    plt.title("Speaking Score Pentagon")
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close(fig) # Explicitly close the figure to free up resources
    buffer.seek(0)
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"
    
def plot_fluency_curve(time_points: list[float], wpm_values: list[float]) -> str:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5)) # Use fig, ax for consistent closing
    ax.plot(time_points, wpm_values, color="blue", linewidth=2)

    # Background zones
    ax.fill_between(time_points, 0, 100, color="#222244", alpha=0.5, label="Slow")
    ax.fill_between(time_points, 100, 160, color="#333366", alpha=0.5, label="Good Pace")
    ax.fill_between(time_points, 160, max(max(wpm_values) + 20, 180), color="#442222", alpha=0.5, label="Too Fast")

    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Words per Minute (WPM)")
    ax.set_title("Fluency Curve")
    ax.legend()
    ax.grid(True)

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close(fig) # Explicitly close the figure to free up resources
    buffer.seek(0)
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"
