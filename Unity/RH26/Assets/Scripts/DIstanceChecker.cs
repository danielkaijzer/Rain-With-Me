using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;

public class DistanceChecker : MonoBehaviour
{
    [Header("Settings")]
    [SerializeField] float distanceThreshold = 10;

    [Header("UDP Settings")]
    [SerializeField] string ipAddress = "127.0.0.1"; // Localhost
    [SerializeField] int port = 5010;

    [Header("References")]
    [SerializeField] Transform leftHand;
    [SerializeField] Transform rightHand;

    // UDP Objects
    private UdpClient udpClient;
    private IPEndPoint remoteEndPoint;

    void Start()
    {
        // Initialize UDP Client once on Start to save performance
        udpClient = new UdpClient();
        remoteEndPoint = new IPEndPoint(IPAddress.Parse(ipAddress), port);

        Debug.Log($"UDP Sender started. Target: {ipAddress}:{port}");
    }

    void Update()
    {
        // 1. Get positions
        Vector3 myPos = transform.position;
        Vector3 leftPos = leftHand.position;
        Vector3 rightPos = rightHand.position;

        // 2. Flatten the Y-axis (height) to ignore it
        myPos.y = 0;
        leftPos.y = 0;
        rightPos.y = 0;

        // 3. Calculate Distances
        float leftDist = Vector3.Distance(myPos, leftPos);
        float rightDist = Vector3.Distance(myPos, rightPos);

        // 4. Find the closest distance (The "Threat" level)
        // Since the Python script just needs to know "Is something close?", 
        // we only need to send the smaller of the two numbers.
        float closestDist = Mathf.Min(leftDist, rightDist);

        Debug.Log($"Closest: {closestDist:F2}");

        // 5. Send raw data over UDP
        // IMPORTANT: We send ONLY the number (e.g., "0.85"). 
        // No "Left:" prefix, so Python can parse it immediately.
        SendString(closestDist.ToString("F2"));
    }

    // Helper method to encode and send data
    private void SendString(string message)
    {
        try
        {
            byte[] data = Encoding.UTF8.GetBytes(message);
            udpClient.Send(data, data.Length, remoteEndPoint);
        }
        catch (System.Exception e)
        {
            Debug.LogError($"UDP Send Error: {e.Message}");
        }
    }

    // IMPORTANT: Close the socket when the game stops or the script is destroyed
    private void OnApplicationQuit()
    {
        if (udpClient != null)
        {
            udpClient.Close();
            udpClient = null;
        }
    }
}