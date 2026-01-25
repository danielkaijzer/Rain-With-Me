using UnityEngine;
using System.Collections;

public class CloudMat : MonoBehaviour
{
    [Header("Fade Settings")]
    public float fadeDuration = 3.0f;

    [Range(0f, 1f)]
    public float startAlpha = 0.0f;   // Starts invisible

    [Range(0f, 1f)]
    public float finalAlpha = 0.8f;   // Stops at 80% opacity (slightly see-through)

    private Renderer objRenderer;

    void Start()
    {
        objRenderer = GetComponent<Renderer>();

        if (objRenderer != null)
        {
            // Set the object to the start alpha immediately
            Color startColor = objRenderer.material.color;
            startColor.a = startAlpha;
            objRenderer.material.color = startColor;

            // Start the fade-in process
            StartCoroutine(FadeToTarget());
        }
    }

    private IEnumerator FadeToTarget()
    {
        float currentTime = 0f;
        Color currentColor = objRenderer.material.color;

        while (currentTime < fadeDuration)
        {
            currentTime += Time.deltaTime;

            // Lerp from startAlpha to finalAlpha (instead of 1.0)
            float newAlpha = Mathf.Lerp(startAlpha, finalAlpha, currentTime / fadeDuration);

            currentColor.a = newAlpha;
            objRenderer.material.color = currentColor;

            yield return null;
        }

        // Ensure it ends up exactly at the final semi-transparent value
        currentColor.a = finalAlpha;
        objRenderer.material.color = currentColor;
    }
}