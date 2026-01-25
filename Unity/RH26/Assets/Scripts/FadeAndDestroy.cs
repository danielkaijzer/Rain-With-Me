using UnityEngine;
using System.Collections;

[RequireComponent(typeof(CanvasGroup))]
public class FadeAndDestroy : MonoBehaviour
{
    [Header("Settings")]
    public float delayBeforeFade = 3f;
    public float fadeDuration = 1f;
    public bool destroyOnFinish = true;

    private CanvasGroup canvasGroup;

    void Start()
    {
        canvasGroup = GetComponent<CanvasGroup>();
        // Start the fading process
        StartCoroutine(FadeSequence());
    }

    private IEnumerator FadeSequence()
    {
        // Wait for the initial 3 seconds
        yield return new WaitForSeconds(delayBeforeFade);

        float currentTime = 0;
        float startAlpha = canvasGroup.alpha;

        // Gradually reduce alpha over the fadeDuration
        while (currentTime < fadeDuration)
        {
            currentTime += Time.deltaTime;
            canvasGroup.alpha = Mathf.Lerp(startAlpha, 0, currentTime / fadeDuration);
            yield return null;
        }

        // Final cleanup
        canvasGroup.alpha = 0;
        
        if (destroyOnFinish)
        {
            Destroy(gameObject);
        }
        else
        {
            gameObject.SetActive(false);
        }
    }
}