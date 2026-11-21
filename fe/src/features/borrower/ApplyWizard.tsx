/**
 * 6-step application wizard for intake workflow:
 * 1. Amount and Purpose
 * 2. Consent per source
 * 3. Live camera capture (3 shots)
 * 4. Document uploads
 * 5. Household budget
 * 6. Review and submit
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import Sheet from '../../components/ui/Sheet'
import StepList from '../../components/ui/StepList'
import Field, { SelectField } from '../../components/ui/Field'

const STEPS = [
  { num: 1, title: 'Amount & Purpose', desc: 'How much do you need?' },
  { num: 2, title: 'Consent', desc: 'Give permission to access your data' },
  { num: 3, title: 'Photos', desc: 'Take 3 photos of your shop' },
  { num: 4, title: 'Documents', desc: 'Upload bills and registration' },
  { num: 5, title: 'Household', desc: 'Monthly expenses and family size' },
  { num: 6, title: 'Review', desc: 'Check and submit' },
]

// ============================================================================
// Step 1: Amount and Purpose
// ============================================================================

const Step1Schema = z.object({
  amount: z.number().min(10000).max(2000000),
  purpose: z.string(),
})

type Step1Data = z.infer<typeof Step1Schema>

function Step1({ onNext, data }: { onNext: (data: Step1Data) => void; data?: Step1Data }) {
  const { register, handleSubmit, formState: { errors } } = useForm<Step1Data>({
    resolver: zodResolver(Step1Schema),
    defaultValues: data,
  })

  return (
    <Sheet>
      <h2>How much do you need?</h2>
      <p className="sub" style={{ marginBottom: '1.5rem' }}>
        We'll assess how much we can lend based on your business records.
      </p>

      <form onSubmit={handleSubmit(onNext)} noValidate>
        <Field
          label="Amount (₹)"
          type="number"
          placeholder="e.g. 200000"
          min={10000}
          step={1000}
          {...register('amount', { valueAsNumber: true })}
          error={errors.amount?.message}
        />

        <SelectField
          label="Purpose"
          options={[
            { value: 'stock', label: 'Stock purchase' },
            { value: 'festival', label: 'Festival stock' },
            { value: 'expansion', label: 'Shop expansion' },
            { value: 'working', label: 'Working capital' },
          ]}
          {...register('purpose')}
          error={errors.purpose?.message}
        />

        <div className="actions" style={{ marginTop: '1.5rem' }}>
          <button type="submit" className="btn red">Next</button>
        </div>
      </form>
    </Sheet>
  )
}

// ============================================================================
// Step 2: Consent per source
// ============================================================================

const Step2Schema = z.object({
  photos: z.boolean(),
  location: z.boolean(),
  bankData: z.boolean(),
  gstData: z.boolean(),
  documents: z.boolean(),
  household: z.boolean(),
})

type Step2Data = z.infer<typeof Step2Schema>

const SOURCES = [
  { key: 'photos', label: 'Live Shop Photos', desc: 'Verify your shop location and inventory' },
  { key: 'location', label: 'Location Data', desc: 'Match photo location with rent agreement' },
  { key: 'bankData', label: 'Bank Data', desc: 'Verify business inflows via Account Aggregator' },
  { key: 'gstData', label: 'GST Filings', desc: 'Verify business turnover' },
  { key: 'documents', label: 'Documents', desc: 'Verify identity and registration' },
  { key: 'household', label: 'Household Details', desc: 'Calculate your household budget' },
]

function Step2({ onNext, data }: { onNext: (data: Step2Data) => void; data?: Step2Data }) {
  const { register, handleSubmit } = useForm<Step2Data>({
    resolver: zodResolver(Step2Schema),
    defaultValues: data || {
      photos: true,
      location: true,
      bankData: true,
      gstData: true,
      documents: true,
      household: true,
    },
  })

  return (
    <Sheet>
      <h2>Permissions</h2>
      <p className="sub" style={{ marginBottom: '1.5rem' }}>
        Each source helps us understand your business. Declining a source is OK—we'll just have lower certainty.
      </p>

      <form onSubmit={handleSubmit(onNext)} noValidate>
        {SOURCES.map(({ key, label, desc }) => (
          <label key={key} className="check" style={{ marginBottom: '1rem', display: 'block' }}>
            <input type="checkbox" {...register(key as keyof Step2Data)} />
            <div>
              <strong>{label}</strong>
              <p style={{ fontSize: '0.85rem', color: '#666', margin: '0.25rem 0 0' }}>{desc}</p>
            </div>
          </label>
        ))}

        <div className="actions" style={{ marginTop: '1.5rem' }}>
          <button type="submit" className="btn red">Next</button>
        </div>
      </form>
    </Sheet>
  )
}

// ============================================================================
// Step 3: Live photos (camera capture)
// ============================================================================

interface PhotoData {
  shopFront?: Blob
  stockShelves?: Blob
  billsLedger?: Blob
}

function Step3({ onNext, data }: { onNext: (data: PhotoData) => void; data?: PhotoData }) {
  const [currentShot, setCurrentShot] = useState<'shopFront' | 'stockShelves' | 'billsLedger'>('shopFront')
  const [preview, setPreview] = useState<string | null>(null)
  const [photos, setPhotos] = useState<PhotoData>(data || {})

  const videoRef = (video: HTMLVideoElement | null) => {
    if (video && !preview) {
      navigator.mediaDevices
        .getUserMedia({ video: { facingMode: 'environment' } })
        .then((stream) => {
          video.srcObject = stream
        })
        .catch((err) => console.error('Camera error:', err))
    }
  }

  function capture() {
    const video = document.querySelector('video') as HTMLVideoElement
    if (!video) return

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.drawImage(video, 0, 0)
      canvas.toBlob((blob) => {
        if (blob) {
          setPhotos((prev) => ({ ...prev, [currentShot]: blob }))
          setPreview(canvas.toDataURL())
        }
      }, 'image/jpeg')
    }
  }

  function nextShot() {
    const shots: (typeof currentShot)[] = ['shopFront', 'stockShelves', 'billsLedger']
    const nextIdx = shots.indexOf(currentShot) + 1
    if (nextIdx < shots.length) {
      setCurrentShot(shots[nextIdx])
      setPreview(null)
    } else {
      onNext(photos)
    }
  }

  const shotLabels = {
    shopFront: 'Shop front',
    stockShelves: 'Stock shelves',
    billsLedger: 'Bills or ledger',
  }

  return (
    <Sheet>
      <h2>Take photos</h2>
      <p className="sub" style={{ marginBottom: '1rem' }}>
        {shotLabels[currentShot]} — write a random code on paper and keep it visible in the frame
      </p>

      {preview ? (
        <div style={{ marginBottom: '1rem' }}>
          <img src={preview} alt="preview" style={{ width: '100%', borderRadius: '4px' }} />
          <div className="actions" style={{ marginTop: '1rem' }}>
            <button className="btn red" onClick={nextShot}>
              {currentShot === 'billsLedger' ? 'Done' : 'Next photo'}
            </button>
            <button className="btn small" onClick={() => setPreview(null)}>
              Retake
            </button>
          </div>
        </div>
      ) : (
        <div>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            style={{ width: '100%', borderRadius: '4px', marginBottom: '1rem' }}
          />
          <button className="btn red" onClick={capture} style={{ width: '100%' }}>
            Capture
          </button>
        </div>
      )}
    </Sheet>
  )
}

// ============================================================================
// Step 4: Documents
// ============================================================================

interface DocumentData {
  electricityBill?: File
  rentReceipt?: File
  udyamCert?: File
  gstReturn?: File
}

function Step4({ onNext, data }: { onNext: (data: DocumentData) => void; data?: DocumentData }) {
  const [docs, setDocs] = useState<DocumentData>(data || {})

  function handleFileChange(field: keyof DocumentData, file: File | undefined) {
    setDocs((prev) => ({ ...prev, [field]: file }))
  }

  return (
    <Sheet>
      <h2>Documents</h2>
      <p className="sub" style={{ marginBottom: '1.5rem' }}>
        Upload bills, registration, and GST returns.
      </p>

      <div>
        <label style={{ display: 'block', marginBottom: '1rem' }}>
          <strong>Electricity bill or rent receipt</strong>
          <input
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={(e) => handleFileChange('electricityBill', e.target.files?.[0])}
            style={{ display: 'block', marginTop: '0.5rem' }}
          />
          {docs.electricityBill && <span style={{ fontSize: '0.85rem', color: '#0a8'}}>{docs.electricityBill.name} ✓</span>}
        </label>

        <label style={{ display: 'block', marginBottom: '1rem' }}>
          <strong>Udyam certificate (optional)</strong>
          <input
            type="file"
            accept=".pdf,.jpg,.jpeg"
            onChange={(e) => handleFileChange('udyamCert', e.target.files?.[0])}
            style={{ display: 'block', marginTop: '0.5rem' }}
          />
          {docs.udyamCert && <span style={{ fontSize: '0.85rem', color: '#0a8' }}>{docs.udyamCert.name} ✓</span>}
        </label>

        <label style={{ display: 'block', marginBottom: '1rem' }}>
          <strong>GST return (GSTR-2B) (optional)</strong>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => handleFileChange('gstReturn', e.target.files?.[0])}
            style={{ display: 'block', marginTop: '0.5rem' }}
          />
          {docs.gstReturn && <span style={{ fontSize: '0.85rem', color: '#0a8' }}>{docs.gstReturn.name} ✓</span>}
        </label>

        <div className="actions" style={{ marginTop: '1.5rem' }}>
          <button
            className="btn red"
            onClick={() => onNext(docs)}
            disabled={!docs.electricityBill}
          >
            Next
          </button>
        </div>
      </div>
    </Sheet>
  )
}

// ============================================================================
// Step 5: Household budget
// ============================================================================

const Step5Schema = z.object({
  familySize: z.number().min(1).max(20),
  monthlyFood: z.number().min(0),
  monthlyRent: z.number().min(0),
  monthlyUtilities: z.number().min(0),
  monthlyEducation: z.number().min(0),
  monthlyHealth: z.number().min(0),
  monthlyOther: z.number().min(0),
})

type Step5Data = z.infer<typeof Step5Schema>

function Step5({ onNext, data }: { onNext: (data: Step5Data) => void; data?: Step5Data }) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<Step5Data>({
    resolver: zodResolver(Step5Schema),
    defaultValues: data || {
      familySize: 4,
      monthlyFood: 5000,
      monthlyRent: 0,
      monthlyUtilities: 1000,
      monthlyEducation: 2000,
      monthlyHealth: 1000,
      monthlyOther: 1000,
    },
  })

  const values = watch()
  const total = Object.entries(values)
    .filter(([k]) => k !== 'familySize')
    .reduce((sum, [, v]) => sum + (v || 0), 0)

  return (
    <Sheet>
      <h2>Household expenses</h2>
      <p className="sub" style={{ marginBottom: '1rem' }}>
        This helps us calculate a safe loan amount for your household.
      </p>

      <form onSubmit={handleSubmit(onNext)} noValidate>
        <Field
          label="Family size"
          type="number"
          min={1}
          max={20}
          {...register('familySize', { valueAsNumber: true })}
          error={errors.familySize?.message}
        />

        <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '1rem' }}>
          Family size is used to calculate your household budget. It is <strong>not</strong> used as a score feature.
        </p>

        <Field
          label="Monthly food (₹)"
          type="number"
          min={0}
          step={100}
          {...register('monthlyFood', { valueAsNumber: true })}
        />

        <Field
          label="Monthly rent (₹)"
          type="number"
          min={0}
          step={100}
          {...register('monthlyRent', { valueAsNumber: true })}
        />

        <Field
          label="Monthly utilities (₹)"
          type="number"
          min={0}
          step={100}
          {...register('monthlyUtilities', { valueAsNumber: true })}
        />

        <Field
          label="Monthly education (₹)"
          type="number"
          min={0}
          step={100}
          {...register('monthlyEducation', { valueAsNumber: true })}
        />

        <Field
          label="Monthly health (₹)"
          type="number"
          min={0}
          step={100}
          {...register('monthlyHealth', { valueAsNumber: true })}
        />

        <Field
          label="Monthly other (₹)"
          type="number"
          min={0}
          step={100}
          {...register('monthlyOther', { valueAsNumber: true })}
        />

        <p style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
          <strong>Total monthly: ₹{total.toLocaleString()}</strong>
        </p>

        <div className="actions" style={{ marginTop: '1.5rem' }}>
          <button type="submit" className="btn red">Next</button>
        </div>
      </form>
    </Sheet>
  )
}

// ============================================================================
// Step 6: Review and submit
// ============================================================================

interface ReviewData {
  step1: Step1Data
  step2: Step2Data
  step3: PhotoData
  step4: DocumentData
  step5: Step5Data
}

function Step6({ allData, onSubmit }: { allData: ReviewData; onSubmit: () => void }) {
  return (
    <Sheet>
      <h2>Review and submit</h2>
      <p className="sub" style={{ marginBottom: '1.5rem' }}>
        Check your information before submitting.
      </p>

      <div style={{ fontSize: '0.9rem', marginBottom: '1.5rem' }}>
        <p><strong>Amount:</strong> ₹{allData.step1.amount.toLocaleString()}</p>
        <p><strong>Purpose:</strong> {allData.step1.purpose}</p>
        <p><strong>Family size:</strong> {allData.step5.familySize}</p>
        <p><strong>Monthly expenses:</strong> ₹{((allData.step5.monthlyFood || 0) + (allData.step5.monthlyRent || 0) + (allData.step5.monthlyUtilities || 0) + (allData.step5.monthlyEducation || 0) + (allData.step5.monthlyHealth || 0) + (allData.step5.monthlyOther || 0)).toLocaleString()}</p>
        <p><strong>Photos:</strong> {Object.keys(allData.step3).length}/3 captured</p>
        <p><strong>Documents:</strong> {Object.keys(allData.step4).length} uploaded</p>
      </div>

      <div className="actions">
        <button className="btn red" onClick={onSubmit}>Confirm & submit</button>
      </div>
    </Sheet>
  )
}

// ============================================================================
// Main wizard
// ============================================================================

export default function ApplyWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState<ReviewData | null>(null)

  function handleStep(stepNum: number, data: any) {
    const newData = {
      ...formData,
      [`step${stepNum}` as keyof ReviewData]: data,
    } as ReviewData
    setFormData(newData)
    setStep(stepNum + 1)
  }

  async function submit() {
    if (!formData) return
    // TODO: Call API to submit application
    navigate('/my/application/1/result')
  }

  return (
    <div style={{ maxWidth: 480, padding: '3rem 0' }}>
      <StepList steps={STEPS} current={step} />

      {step === 1 && <Step1 onNext={(d) => handleStep(1, d)} data={formData?.step1} />}
      {step === 2 && <Step2 onNext={(d) => handleStep(2, d)} data={formData?.step2} />}
      {step === 3 && <Step3 onNext={(d) => handleStep(3, d)} data={formData?.step3} />}
      {step === 4 && <Step4 onNext={(d) => handleStep(4, d)} data={formData?.step4} />}
      {step === 5 && <Step5 onNext={(d) => handleStep(5, d)} data={formData?.step5} />}
      {step === 6 && formData && <Step6 allData={formData} onSubmit={submit} />}
    </div>
  )
}
