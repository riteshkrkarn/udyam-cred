/**
 * Photo Service: Handles photo upload with geo-location and challenge code verification
 * Integrates with backend photo endpoints for verification-first lending
 */

export interface PhotoUploadOptions {
  applicationId: string
  photoType: 'shop_front' | 'stock_shelves' | 'bills_ledger'
  photoBlob: Blob
  locationLat: number
  locationLng: number
  randomCode: string
  timestamp: string
}

export interface PhotoUploadResponse {
  photo_id: string
  application_id: string
  photo_type: string
  photo_path: string
  location_lat: number
  location_lng: number
  verification_status: 'verified' | 'pending' | 'failed'
  code_verified: boolean
  location_confidence: number
  message?: string
}

export interface PhotoVerificationResult {
  photo_id: string
  code_verified: boolean
  location_verified: boolean
  location_lat: number
  location_lng: number
  location_confidence: number
  distance_from_rent_meters?: number
  issues: string[]
}

/**
 * Upload a photo with geolocation and challenge code
 * Sends to backend for verification
 */
export async function uploadPhoto(
  options: PhotoUploadOptions,
  apiBase: string = '/api'
): Promise<PhotoUploadResponse> {
  const formData = new FormData()

  // Append photo and metadata
  formData.append('photo', options.photoBlob, `${options.photoType}.jpg`)
  formData.append('photo_type', options.photoType)
  formData.append('location_lat', options.locationLat.toString())
  formData.append('location_lng', options.locationLng.toString())
  formData.append('random_code', options.randomCode)
  formData.append('timestamp', options.timestamp)

  try {
    const response = await fetch(
      `${apiBase}/applications/${options.applicationId}/photos`,
      {
        method: 'POST',
        body: formData,
        headers: {
          // Note: Don't set Content-Type, let browser set it with boundary
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Photo upload failed: ${response.statusText}`)
    }

    const data: PhotoUploadResponse = await response.json()
    return data
  } catch (error) {
    console.error('Photo upload error:', error)
    throw error
  }
}

/**
 * Get all photos for an application
 */
export async function getPhotos(
  applicationId: string,
  apiBase: string = '/api'
): Promise<PhotoUploadResponse[]> {
  try {
    const response = await fetch(`${apiBase}/applications/${applicationId}/photos`)

    if (!response.ok) {
      throw new Error(`Failed to fetch photos: ${response.statusText}`)
    }

    const data = await response.json()
    return data.photos || []
  } catch (error) {
    console.error('Error fetching photos:', error)
    throw error
  }
}

/**
 * Get photo verification result
 */
export async function getPhotoVerification(
  applicationId: string,
  photoId: string,
  apiBase: string = '/api'
): Promise<PhotoVerificationResult> {
  try {
    const response = await fetch(
      `${apiBase}/applications/${applicationId}/photos/${photoId}/verification`
    )

    if (!response.ok) {
      throw new Error(`Failed to get verification: ${response.statusText}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    console.error('Error getting verification:', error)
    throw error
  }
}

/**
 * Capture photo from device camera
 * Returns blob and geolocation
 */
export async function capturePhotoFromCamera(): Promise<{
  blob: Blob
  latitude: number
  longitude: number
  timestamp: string
}> {
  return new Promise((resolve, reject) => {
    // Request camera access
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' } })
      .then(stream => {
        const video = document.createElement('video')
        video.srcObject = stream
        video.play()

        // Get geolocation
        if (navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(
            position => {
              const canvas = document.createElement('canvas')
              canvas.width = video.videoWidth
              canvas.height = video.videoHeight
              const ctx = canvas.getContext('2d')

              if (ctx) {
                ctx.drawImage(video, 0, 0)
                canvas.toBlob(blob => {
                  if (blob) {
                    // Stop video stream
                    stream.getTracks().forEach(track => track.stop())

                    resolve({
                      blob,
                      latitude: position.coords.latitude,
                      longitude: position.coords.longitude,
                      timestamp: new Date().toISOString(),
                    })
                  } else {
                    reject(new Error('Failed to create blob from canvas'))
                  }
                }, 'image/jpeg')
              } else {
                reject(new Error('Failed to get canvas context'))
              }
            },
            error => {
              reject(new Error(`Geolocation error: ${error.message}`))
            }
          )
        } else {
          reject(new Error('Geolocation not supported'))
        }
      })
      .catch(error => {
        reject(new Error(`Camera access denied: ${error.message}`))
      })
  })
}

/**
 * Generate random challenge code (4-6 alphanumeric characters)
 */
export function generateChallengeCode(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
  let code = ''
  for (let i = 0; i < 6; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return code
}

/**
 * Verify photo was taken within reasonable distance of expected location
 * Used for client-side validation before sending to backend
 */
export function calculateDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): number {
  // Haversine formula for distance in meters
  const R = 6371000 // Earth radius in meters
  const φ1 = (lat1 * Math.PI) / 180
  const φ2 = (lat2 * Math.PI) / 180
  const Δφ = ((lat2 - lat1) * Math.PI) / 180
  const Δλ = ((lng2 - lng1) * Math.PI) / 180

  const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  const distance = R * c

  return distance
}

/**
 * Validate location is within tolerance (default 500m)
 */
export function isLocationWithinTolerance(
  photoLat: number,
  photoLng: number,
  expectedLat: number,
  expectedLng: number,
  toleranceMeters: number = 500
): boolean {
  const distance = calculateDistance(photoLat, photoLng, expectedLat, expectedLng)
  return distance <= toleranceMeters
}

/**
 * Extract EXIF data from photo (if available)
 * Returns geolocation if embedded in photo metadata
 */
export async function extractPhotoExif(
  blob: Blob
): Promise<{ latitude?: number; longitude?: number }> {
  // Note: This requires piexifjs or similar library
  // For now, return empty object (geolocation will come from device GPS)
  return {}
}

/**
 * Batch upload multiple photos with retry logic
 */
export async function batchUploadPhotos(
  applicationId: string,
  photos: PhotoUploadOptions[],
  apiBase: string = '/api'
): Promise<PhotoUploadResponse[]> {
  const results: PhotoUploadResponse[] = []
  const maxRetries = 3

  for (const photo of photos) {
    let retries = 0
    let lastError: Error | null = null

    while (retries < maxRetries) {
      try {
        const result = await uploadPhoto(photo, apiBase)
        results.push(result)
        break
      } catch (error) {
        lastError = error as Error
        retries++
        // Wait before retry (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, retries) * 1000))
      }
    }

    if (retries === maxRetries && lastError) {
      console.error(
        `Failed to upload photo ${photo.photoType} after ${maxRetries} retries:`,
        lastError
      )
      // Continue with other photos instead of failing entire batch
    }
  }

  return results
}
